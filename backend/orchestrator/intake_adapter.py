"""Bridges a confirmed MaintenanceSignal (image path — domain-multimodal-intake.md: extraction ->
normalised into MaintenanceSignal -> shown to the user for confirmation -> entering a workflow)
into a real Supervisor run. Caller MUST have already obtained on-screen confirmation — this
function does not itself confirm anything, it enforces that confirmation already happened.
The voice path's 6 intents are commands against EXISTING incidents/tickets (approve/reject/show/
what-changed/start-scenario), a different flow from "bootstrap a new incident" and not routed
through this adapter.
"""
import json
import os
import uuid

from orchestrator.contracts import MaintenanceSignal
from orchestrator.supervisor import run_workflow

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")


def _load_ci(ci_id: str) -> dict:
    with open(os.path.join(DATA_DIR, "cmdb.json"), encoding="utf-8") as f:
        cis = {ci["id"]: ci for ci in json.load(f)["cis"]}
    if ci_id not in cis:
        raise ValueError(f"signal referenced unknown CI {ci_id!r}")
    return cis[ci_id]


def _alerts_for_ci(ci_id: str, signal: MaintenanceSignal) -> list[dict]:
    with open(os.path.join(DATA_DIR, "alerts.json"), encoding="utf-8") as f:
        alerts = json.load(f)
    matching = [a for a in alerts if a["ci_id"] == ci_id and a["category"] == "fault"]
    if matching:
        return matching
    # No pre-existing synthetic alert for this CI — the image itself IS the triggering evidence,
    # so synthesize a minimal alert record citing the signal, never fabricating a fake source system.
    return [{
        "id": f"ALERT-FROM-{signal.signal_id}", "source": "image_intake", "ci_id": ci_id,
        "category": "fault", "severity": "warning", "received_at": signal.received_at,
        "raw_payload": {"extracted_from_image": signal.extracted_text},
    }]


async def start_workflow_from_confirmed_signal(signal: MaintenanceSignal, workflow_type: str = "incident") -> dict:
    if signal.requires_human_confirmation:
        raise ValueError(
            f"signal {signal.signal_id} still requires human confirmation — "
            "do not call this until the on-screen confirmation step has completed"
        )
    if not signal.candidate_ci_refs:
        raise ValueError(f"signal {signal.signal_id} has no resolvable CI reference, cannot start a workflow")

    ci_id = signal.candidate_ci_refs[0]
    ci = _load_ci(ci_id)
    alerts = _alerts_for_ci(ci_id, signal)
    incident_id = f"INC-{signal.signal_id}-{uuid.uuid4().hex[:4]}"
    outcome = await run_workflow(incident_id=incident_id, ci=ci, alerts=alerts, workflow_type=workflow_type)
    return {**outcome, "incident_id": incident_id}  # additive — callers keyed on status/trace still work
