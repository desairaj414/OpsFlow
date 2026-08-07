"""CMDB simulator [MOCK-P1] — a thin-but-authentic stand-in for a CMDB system. NOT a real CMDB;
labelled as a simulator in the UI/README, never presented as real SaaS. Serves the synthetic
CI inventory generated in backend/data_gen/cmdb.py. `propose_ci_update` deliberately does NOT
mutate the CI directly — per api-contract.md, CI writes require human approval before landing,
so this simulator only records the proposal for a human/approval flow to act on later.

    python mcp_servers/simulators/cmdb.py         # boots on :9004
    python mcp_servers/simulators/cmdb.py --test  # in-process self-test, no port bound
"""
import json
import os
import sys
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")

app = FastAPI(title="CMDB Simulator [MOCK-P1] — not a real CMDB")

_CIS: dict[str, dict] = {}
_RELATIONSHIPS: dict[str, list[dict]] = {}
_PENDING_UPDATES: list[dict] = []


def _load() -> None:
    if _CIS:
        return
    with open(os.path.join(DATA_DIR, "cmdb.json"), encoding="utf-8") as f:
        data = json.load(f)
    for ci in data["cis"]:
        _CIS[ci["id"]] = ci
    for rel in data["relationships"]:
        _RELATIONSHIPS.setdefault(rel["ci_id"], []).append(rel)


class ProposeUpdateRequest(BaseModel):
    field: str
    proposed_value: str
    reason: str
    actor: str


@app.get("/cmdb_ci/{ci_id}")
def get_ci(ci_id: str):
    _load()
    ci = _CIS.get(ci_id)
    if not ci:
        raise HTTPException(status_code=404, detail=f"no CI {ci_id}")
    return ci


@app.get("/cmdb_ci/{ci_id}/relationships")
def get_relationships(ci_id: str):
    _load()
    if ci_id not in _CIS:
        raise HTTPException(status_code=404, detail=f"no CI {ci_id}")
    return {"ci_id": ci_id, "relationships": _RELATIONSHIPS.get(ci_id, [])}


@app.post("/cmdb_ci/{ci_id}/propose_update")
def propose_ci_update(ci_id: str, req: ProposeUpdateRequest):
    """Records the proposal only — does NOT mutate the CI. Real write happens only after
    human approval, via a separate (not-yet-built) approval-apply step (see api-contract.md)."""
    _load()
    if ci_id not in _CIS:
        raise HTTPException(status_code=404, detail=f"no CI {ci_id}")
    proposal = {
        "proposal_id": f"PROP-{len(_PENDING_UPDATES) + 1:04d}",
        "ci_id": ci_id,
        "field": req.field,
        "current_value": _CIS[ci_id].get(req.field),
        "proposed_value": req.proposed_value,
        "reason": req.reason,
        "actor": req.actor,
        "status": "pending_approval",
        "proposed_at": datetime.now(timezone.utc).isoformat(),
    }
    _PENDING_UPDATES.append(proposal)
    return proposal


@app.get("/health")
def health():
    return {"status": "ok", "simulator": "cmdb"}


def _self_test() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app)

    r = client.get("/cmdb_ci/CI-0001")
    assert r.status_code == 200, r.text
    ci = r.json()
    assert set(["id", "name", "type", "owner", "environment", "criticality", "patch_level"]).issubset(ci.keys())
    print(f"PASS get_ci: {ci['id']} ({ci['type']})")

    r = client.get("/cmdb_ci/CI-0001/relationships")
    assert r.status_code == 200
    print(f"PASS get_relationships: {len(r.json()['relationships'])} relationships for CI-0001")

    r = client.post("/cmdb_ci/CI-0001/propose_update", json={
        "field": "patch_level", "proposed_value": "9.9.9", "reason": "test proposal", "actor": "smoke-test",
    })
    assert r.status_code == 200, r.text
    proposal = r.json()
    assert proposal["status"] == "pending_approval"
    print(f"PASS propose_ci_update: {proposal['proposal_id']} (status={proposal['status']})")

    # Confirm the proposal did NOT mutate the actual CI — this is the human-approval gate.
    r = client.get("/cmdb_ci/CI-0001")
    assert r.json()["patch_level"] != "9.9.9", "propose_ci_update must not mutate the CI directly"
    print("PASS propose_ci_update does not mutate the CI (human-approval gate intact)")

    r = client.get("/cmdb_ci/CI-9999")
    assert r.status_code == 404
    print("PASS get_ci 404 for unknown CI")

    print("\nSELF-TEST PASSED: CMDB simulator endpoints all working.")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _self_test()
    else:
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=9004)
