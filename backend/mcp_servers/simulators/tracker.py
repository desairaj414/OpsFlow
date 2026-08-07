"""Tracker simulator [MOCK-P1] — a thin-but-authentic stand-in for a Jira-style issue tracker.
NOT real Jira; labelled as a simulator in the UI/README, never presented as real SaaS. Field
shapes deliberately mirror Jira's real REST API conventions (`key` like "OPS-12",
`fields.status.name`, `fields.issuetype.name`) — field-name fidelity is the point, not full
feature parity. Seeded from a subset of the synthetic ticket history (tuning_task rows map
naturally onto tracked issues); mutated in-memory during the demo.

    python mcp_servers/simulators/tracker.py         # boots on :9003
    python mcp_servers/simulators/tracker.py --test  # in-process self-test, no port bound
"""
import csv
import os
import sys
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
PROJECT_KEY = "OPS"

# Jira-style workflow: Open -> In Progress -> Done, transition ids are strings per Jira convention.
_TRANSITIONS = {"1": "In Progress", "2": "Done", "3": "Open"}
_STORE: dict[str, dict] = {}  # issue key -> issue, in-memory


def _seed_store() -> None:
    path = os.path.join(DATA_DIR, "tickets.csv")
    if not os.path.exists(path) or _STORE:
        return
    with open(path, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["type"] == "tuning_task"]
    for i, row in enumerate(rows, start=1):
        key = f"{PROJECT_KEY}-{i}"
        status = "Done" if row["status"] == "closed" else ("In Progress" if row["status"] == "in_progress" else "Open")
        _STORE[key] = {
            "key": key,
            "fields": {
                "summary": row["short_description"],
                "status": {"name": status},
                "issuetype": {"name": "Task"},
                "priority": {"name": row["priority"]},
                "cmdb_ci": row["ci_id"],
                "created": row["opened_at"],
            },
            "links": [],
        }


class CreateIssueRequest(BaseModel):
    summary: str
    priority: str = "P3"
    cmdb_ci: str


class LinkIssueRequest(BaseModel):
    target_key: str
    link_type: str = "relates to"


class TransitionRequest(BaseModel):
    transition_id: str


app = FastAPI(title="Tracker Simulator [MOCK-P1] — not real Jira")


@app.get("/rest/api/2/issue/{key}")
def get_issue(key: str):
    _seed_store()
    issue = _STORE.get(key)
    if not issue:
        raise HTTPException(status_code=404, detail=f"no issue {key}")
    return issue


@app.post("/rest/api/2/issue")
def create_issue(req: CreateIssueRequest):
    _seed_store()
    key = f"{PROJECT_KEY}-{len(_STORE) + 1}"
    issue = {
        "key": key,
        "fields": {
            "summary": req.summary,
            "status": {"name": "Open"},
            "issuetype": {"name": "Task"},
            "priority": {"name": req.priority},
            "cmdb_ci": req.cmdb_ci,
            "created": datetime.now(timezone.utc).isoformat(),
        },
        "links": [],
    }
    _STORE[key] = issue
    return issue


@app.post("/rest/api/2/issueLink")
def link_issue(source_key: str, req: LinkIssueRequest):
    _seed_store()
    source = _STORE.get(source_key)
    if not source or req.target_key not in _STORE:
        raise HTTPException(status_code=404, detail="source or target issue not found")
    source["links"].append({"type": req.link_type, "target_key": req.target_key})
    return source


@app.post("/rest/api/2/issue/{key}/transitions")
def transition_issue(key: str, req: TransitionRequest):
    _seed_store()
    issue = _STORE.get(key)
    if not issue:
        raise HTTPException(status_code=404, detail=f"no issue {key}")
    new_status = _TRANSITIONS.get(req.transition_id)
    if not new_status:
        raise HTTPException(status_code=400, detail=f"unknown transition_id {req.transition_id}")
    issue["fields"]["status"]["name"] = new_status
    return issue


@app.get("/health")
def health():
    return {"status": "ok", "simulator": "tracker"}


def _self_test() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app)

    _seed_store()
    assert len(_STORE) > 0, "no issues seeded — check tickets.csv has tuning_task rows"
    print(f"PASS seed: {len(_STORE)} issues")

    sample_key = next(iter(_STORE))
    r = client.get(f"/rest/api/2/issue/{sample_key}")
    assert r.status_code == 200, r.text
    assert "fields" in r.json() and "status" in r.json()["fields"]
    print(f"PASS get_issue: {sample_key}")

    r = client.post("/rest/api/2/issue", json={"summary": "Test-created issue", "cmdb_ci": "CI-0001"})
    assert r.status_code == 200, r.text
    new_key = r.json()["key"]
    print(f"PASS create_issue: {new_key}")

    r = client.post(f"/rest/api/2/issue/{new_key}/transitions", json={"transition_id": "1"})
    assert r.status_code == 200
    assert r.json()["fields"]["status"]["name"] == "In Progress"
    print(f"PASS transition_issue: {new_key} -> In Progress")

    r = client.post(f"/rest/api/2/issueLink?source_key={new_key}", json={"target_key": sample_key})
    assert r.status_code == 200, r.text
    assert len(r.json()["links"]) == 1
    print(f"PASS link_issue: {new_key} -> {sample_key}")

    r = client.get("/rest/api/2/issue/OPS-99999")
    assert r.status_code == 404
    print("PASS get_issue 404 for unknown key")

    print("\nSELF-TEST PASSED: Tracker simulator endpoints all working.")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _self_test()
    else:
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=9003)
