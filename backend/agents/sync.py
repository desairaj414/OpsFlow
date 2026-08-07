"""Sync agent — writes the outcome back to every simulated system as one consistent record
(domain-agents.md). Deterministic: recording an already-decided outcome is not a reasoning task,
no LLM call here.
"""
from datetime import datetime, timezone

import mcp_servers.cmdb_mcp as cmdb_mcp
import mcp_servers.itsm_mcp as itsm_mcp
from orchestrator.contracts import SpecialistResult
from orchestrator.limits import TurnTracker

_RESOLVED_STATE = "7"    # ServiceNow-style state code, see mcp_servers/simulators/itsm.py
_IN_PROGRESS_STATE = "2"


async def run_sync(incident_id: str, sys_id: str, ci_id: str, verification_status: str, plan: dict) -> SpecialistResult:
    tracker = TurnTracker("sync")
    tracker.use_turn()

    note = f"Verification status: {verification_status}. Plan runbook_id={plan.get('runbook_id', '')}, steps={len(plan.get('steps', []))}."
    await itsm_mcp.add_work_note(sys_id=sys_id, note=note, actor="agent:sync")
    new_state = _RESOLVED_STATE if verification_status == "verified_resolved" else _IN_PROGRESS_STATE
    ticket_result = await itsm_mcp.update_ticket(sys_id=sys_id, state=new_state)

    cmdb_proposal = None
    if verification_status == "verified_resolved":
        cmdb_proposal = await cmdb_mcp.propose_ci_update(
            ci_id=ci_id, field="last_verified_at", proposed_value=datetime.now(timezone.utc).isoformat(),
            reason=f"Resolved via {incident_id}", actor="agent:sync",
        )

    return SpecialistResult(
        agent_name="sync", incident_id=incident_id,
        result={"ticket": ticket_result["result"], "cmdb_proposal": cmdb_proposal},
        cited_artifact_ids=[sys_id, ci_id], confidence=1.0,
        turns_used=tracker.turns_used, termination_reason="sync_complete",
    )
