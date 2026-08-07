"""Phase 1 gate script (PRD step 9) — an AGENT-FREE, deterministic walk of one full incident
scenario through all 4 MCP tool sets end to end. Proves the tool/integration layer works before
any agent code exists (Phase 3). Wires each MCP server's tools directly to its simulator over an
in-process ASGI transport (same pattern each *_mcp.py uses for its own --test), so this needs no
separately-running server processes on ports 9001-9004.

    python scripts/gate_scenario.py
"""
import asyncio
import json
import os
import sys

import httpx

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

import mcp_servers.cmdb_mcp as cmdb_mcp  # noqa: E402
import mcp_servers.itsm_mcp as itsm_mcp  # noqa: E402
import mcp_servers.monitoring_mcp as monitoring_mcp  # noqa: E402
import mcp_servers.simulators.cmdb as cmdb_sim  # noqa: E402
import mcp_servers.simulators.itsm as itsm_sim  # noqa: E402
import mcp_servers.simulators.monitoring as monitoring_sim  # noqa: E402
import mcp_servers.simulators.tracker as tracker_sim  # noqa: E402
import mcp_servers.tracker_mcp as tracker_mcp  # noqa: E402


def _wire_in_process(mcp_module, sim_module) -> None:
    mcp_module._client = httpx.AsyncClient(transport=httpx.ASGITransport(app=sim_module.app), base_url="http://sim")


async def run_scenario() -> None:
    _wire_in_process(monitoring_mcp, monitoring_sim)
    _wire_in_process(itsm_mcp, itsm_sim)
    _wire_in_process(tracker_mcp, tracker_sim)
    _wire_in_process(cmdb_mcp, cmdb_sim)

    print("=== GATE SCENARIO: incident resolution, agent-free, all 4 MCP tool sets ===\n")

    # 1. Correlate: find a fault alert to react to (deterministic pick — first fault alert).
    alerts_result = await monitoring_mcp.list_alerts(category="fault")
    alert = alerts_result["data"]["alerts"][0]
    ci_id = alert["ci_id"]
    print(f"[1/8] Monitoring.list_alerts -> {alert['id']} on {ci_id} (severity={alert['severity']})")

    # 2. Enrich: pull the CI and its relationships (evidence for the diagnosis).
    ci = await cmdb_mcp.get_ci(ci_id=ci_id)
    relationships = await cmdb_mcp.get_relationships(ci_id=ci_id)
    print(f"[2/8] CMDB.get_ci -> {ci['id']} ({ci['type']}, {ci['environment']}, criticality={ci['criticality']})")
    print(f"[3/8] CMDB.get_relationships -> {len(relationships['relationships'])} related CIs")

    # 3. Diagnose (deterministic evidence citation, no LLM at gate-script stage — agents come Phase 3).
    evidence_ids = [alert["id"], ci["id"]]
    diagnosis = f"Fault alert {alert['id']} on {ci['id']} ({ci['type']}): {alert['raw_payload']}"
    print(f"[4/8] Diagnosis drafted, cited_artifact_ids={evidence_ids}")

    # 4. Plan + Gate + Execute (as a ticket, standing in for the workflow record).
    ticket_result = await itsm_mcp.create_ticket(
        short_description=f"Auto-drafted from {alert['id']}: {ci['name']}",
        priority="P2", cmdb_ci=ci_id,
    )
    sys_id = ticket_result["result"]["sys_id"]
    print(f"[5/8] ITSM.create_ticket -> {sys_id}")

    note_result = await itsm_mcp.add_work_note(sys_id=sys_id, note=diagnosis, actor="gate_scenario.py")
    print(f"[6/8] ITSM.add_work_note -> {len(note_result['result']['work_notes'])} note(s) on {sys_id}")

    # 5. Sync: propose a CMDB update as the follow-up action (stays pending — human-approval gate).
    proposal = await cmdb_mcp.propose_ci_update(
        ci_id=ci_id, field="last_verified_at", proposed_value="scenario-run-timestamp",
        reason=f"Verified during resolution of {sys_id}", actor="gate_scenario.py",
    )
    print(f"[7/8] CMDB.propose_ci_update -> {proposal['proposal_id']} (status={proposal['status']}, NOT auto-applied)")

    # 6. Verify + close.
    close_result = await itsm_mcp.update_ticket(sys_id=sys_id, state="7")
    print(f"[8/8] ITSM.update_ticket -> {sys_id} closed at {close_result['result']['closed_at']}")

    print("\n=== SCENARIO COMPLETE — all 4 MCP tool sets exercised, evidence cited, human-approval gate intact ===")

    # Hard assertions — this IS the gate, not just a demo print.
    assert ticket_result["result"]["sys_id"] == sys_id
    assert close_result["result"]["state"] == "7"
    assert proposal["status"] == "pending_approval"
    final_ci = await cmdb_mcp.get_ci(ci_id=ci_id)
    assert final_ci["last_verified_at"] != "scenario-run-timestamp", "propose_ci_update must never auto-apply"
    print("\nGATE PASSED: ticket created and closed, CMDB proposal recorded but not auto-applied.")


if __name__ == "__main__":
    asyncio.run(run_scenario())
