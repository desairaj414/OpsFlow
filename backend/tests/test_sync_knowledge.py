"""Unit tests for the Sync and Knowledge agents, against the in-process-wired simulators and the
real data/app.db (negative_kb_entries insert is a real SQLite write, reverted after the test)."""
import asyncio
import os
import sqlite3

from agents.knowledge import run_knowledge
from agents.sync import run_sync
from orchestrator.mcp_wiring import wire_all_in_process

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "app.db")


def test_sync_closes_ticket_on_verified_resolved():
    wire_all_in_process()
    result = asyncio.run(run_sync(
        incident_id="INC-TEST-SYNC-1", sys_id="TCK-0001", ci_id="CI-0001",
        verification_status="verified_resolved", plan={"runbook_id": "RB-001", "steps": [{"step_no": 1}]},
    ))
    assert result.agent_name == "sync"
    assert result.result["ticket"]["state"] == "7"  # resolved state code
    assert result.result["cmdb_proposal"] is not None
    assert result.result["cmdb_proposal"]["status"] == "pending_approval"  # never auto-applied


def test_sync_keeps_ticket_in_progress_on_symptom_suppressed():
    wire_all_in_process()
    result = asyncio.run(run_sync(
        incident_id="INC-TEST-SYNC-2", sys_id="TCK-0002", ci_id="CI-0002",
        verification_status="symptom_suppressed", plan={"runbook_id": "RB-001", "steps": []},
    ))
    assert result.result["ticket"]["state"] == "2"  # in_progress, NOT closed
    assert result.result["cmdb_proposal"] is None  # no CMDB update proposed for an unresolved incident


def test_knowledge_seeds_negative_kb_on_symptom_suppressed():
    conn = sqlite3.connect(DB_PATH)
    before_count = conn.execute("SELECT COUNT(*) FROM negative_kb_entries").fetchone()[0]
    conn.close()

    result = asyncio.run(run_knowledge(
        incident_id="INC-TEST-KNOW-1", ci_class="db-server", verification_status="symptom_suppressed",
        failure_signature="memory leak", attempted_fix="restarted service",
    ))
    assert result.result["negative_kb_entry"] is not None
    assert result.result["negative_kb_entry"]["ci_class"] == "db-server"

    conn = sqlite3.connect(DB_PATH)
    try:
        after_count = conn.execute("SELECT COUNT(*) FROM negative_kb_entries").fetchone()[0]
        assert after_count == before_count + 1
        row = conn.execute("SELECT source_incident_id FROM negative_kb_entries WHERE id = ?", (result.result["negative_kb_entry"]["id"],)).fetchone()
        assert row[0] == "INC-TEST-KNOW-1"
    finally:
        # Clean up the test-inserted row so repeated test runs don't accumulate junk in app.db.
        conn.execute("DELETE FROM negative_kb_entries WHERE id = ?", (result.result["negative_kb_entry"]["id"],))
        conn.commit()
        conn.close()


def test_knowledge_does_not_seed_negative_kb_on_verified_resolved():
    result = asyncio.run(run_knowledge(incident_id="INC-TEST-KNOW-2", ci_class="db-server", verification_status="verified_resolved"))
    assert result.result["negative_kb_entry"] is None
