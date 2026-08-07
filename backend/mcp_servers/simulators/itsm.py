"""ITSM simulator [MOCK-P1] — a thin-but-authentic stand-in for a ServiceNow-style ITSM system.
NOT real ServiceNow; labelled as a simulator in the UI/README, never presented as real SaaS.
Field shapes deliberately mirror ServiceNow's real Table API conventions (`sys_id`, `result`
envelope, `state` as a string code) — field-name fidelity is the point, not full feature parity.
Seeded from the synthetic ticket history (backend/data_gen/tickets.py); mutated in-memory during
the demo (create/update/work-notes), never persisted back to the seed file.

    python mcp_servers/simulators/itsm.py         # boots on :9002
    python mcp_servers/simulators/itsm.py --test  # in-process self-test, no port bound
"""
import csv
import os
import sys
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")

app = FastAPI(title="ITSM Simulator [MOCK-P1] — not real ServiceNow")

# ServiceNow state codes (subset, real convention): 1=New, 2=In Progress, 6=Resolved, 7=Closed
_STATE_CODE = {"open": "1", "in_progress": "2", "closed": "7"}
_STORE: dict[str, dict] = {}  # sys_id -> ticket, in-memory, mutated during the demo


def _seed_store() -> None:
    path = os.path.join(DATA_DIR, "tickets.csv")
    if not os.path.exists(path) or _STORE:
        return
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sys_id = row["sys_id"]
            _STORE[sys_id] = {
                "sys_id": sys_id,
                "short_description": row["short_description"],
                "state": _STATE_CODE.get(row["status"], "1"),
                "priority": row["priority"],
                "cmdb_ci": row["ci_id"],
                "opened_at": row["opened_at"],
                "closed_at": row["closed_at"] or None,
                "sys_class_name": row["type"],
                "work_notes": [],
            }


class CreateTicketRequest(BaseModel):
    short_description: str
    priority: str
    cmdb_ci: str
    sys_class_name: str = "incident"


class UpdateTicketRequest(BaseModel):
    state: str | None = None
    priority: str | None = None


class WorkNoteRequest(BaseModel):
    note: str
    actor: str


@app.get("/api/now/table/incident")
def get_ticket_list(cmdb_ci: str | None = None, state: str | None = None):
    _seed_store()
    results = list(_STORE.values())
    if cmdb_ci:
        results = [t for t in results if t["cmdb_ci"] == cmdb_ci]
    if state:
        results = [t for t in results if t["state"] == state]
    return {"result": results}


@app.get("/api/now/table/incident/{sys_id}")
def get_ticket(sys_id: str):
    _seed_store()
    ticket = _STORE.get(sys_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"no ticket {sys_id}")
    return {"result": ticket}


@app.post("/api/now/table/incident")
def create_ticket(req: CreateTicketRequest):
    _seed_store()
    sys_id = f"TCK-{len(_STORE) + 1:04d}"
    ticket = {
        "sys_id": sys_id,
        "short_description": req.short_description,
        "state": _STATE_CODE["open"],
        "priority": req.priority,
        "cmdb_ci": req.cmdb_ci,
        "opened_at": datetime.now(timezone.utc).isoformat(),
        "closed_at": None,
        "sys_class_name": req.sys_class_name,
        "work_notes": [],
    }
    _STORE[sys_id] = ticket
    return {"result": ticket}


@app.patch("/api/now/table/incident/{sys_id}")
def update_ticket(sys_id: str, req: UpdateTicketRequest):
    _seed_store()
    ticket = _STORE.get(sys_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"no ticket {sys_id}")
    if req.state is not None:
        ticket["state"] = req.state
        if req.state == _STATE_CODE["closed"]:
            ticket["closed_at"] = datetime.now(timezone.utc).isoformat()
    if req.priority is not None:
        ticket["priority"] = req.priority
    return {"result": ticket}


@app.post("/api/now/table/incident/{sys_id}/work_notes")
def add_work_note(sys_id: str, req: WorkNoteRequest):
    _seed_store()
    ticket = _STORE.get(sys_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"no ticket {sys_id}")
    entry = {"note": req.note, "actor": req.actor, "at": datetime.now(timezone.utc).isoformat()}
    ticket["work_notes"].append(entry)
    return {"result": ticket}


@app.get("/health")
def health():
    return {"status": "ok", "simulator": "itsm"}


def _self_test() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app)

    r = client.get("/api/now/table/incident")
    assert r.status_code == 200, r.text
    seeded = r.json()["result"]
    assert len(seeded) > 400, f"expected seeded tickets, got {len(seeded)}"
    print(f"PASS get_ticket_list (seeded): {len(seeded)} tickets")

    sample_id = seeded[0]["sys_id"]
    r = client.get(f"/api/now/table/incident/{sample_id}")
    assert r.status_code == 200
    print(f"PASS get_ticket: {sample_id}")

    r = client.post("/api/now/table/incident", json={
        "short_description": "Test-created ticket", "priority": "P2", "cmdb_ci": "CI-0001",
    })
    assert r.status_code == 200, r.text
    new_id = r.json()["result"]["sys_id"]
    print(f"PASS create_ticket: {new_id}")

    r = client.patch(f"/api/now/table/incident/{new_id}", json={"state": "7"})
    assert r.status_code == 200
    assert r.json()["result"]["closed_at"] is not None
    print(f"PASS update_ticket (close): {new_id}")

    r = client.post(f"/api/now/table/incident/{new_id}/work_notes", json={"note": "closed via test", "actor": "smoke-test"})
    assert r.status_code == 200
    assert len(r.json()["result"]["work_notes"]) == 1
    print(f"PASS add_work_note: {new_id}")

    r = client.get("/api/now/table/incident/TCK-9999")
    assert r.status_code == 404
    print("PASS get_ticket 404 for unknown sys_id")

    print("\nSELF-TEST PASSED: ITSM simulator endpoints all working.")


if __name__ == "__main__":
    if "--test" in sys.argv:
        _self_test()
    else:
        import uvicorn

        uvicorn.run(app, host="0.0.0.0", port=9002)
