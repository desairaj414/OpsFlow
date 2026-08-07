"""Knowledge (+ Negative KB) agent — captures the outcome; on rejection/failure, seeds the
Negative KB scoped to CI class + failure signature (domain-agents.md), so a remediation that
failed once is remembered, not just successes. Deterministic, no LLM.
"""
import os
import sqlite3

from orchestrator.contracts import SpecialistResult
from orchestrator.limits import TurnTracker

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(REPO_ROOT, "data", "app.db")


def _next_negkb_id(conn: sqlite3.Connection) -> str:
    cur = conn.execute("SELECT COUNT(*) FROM negative_kb_entries")
    return f"NEGKB-RUNTIME-{cur.fetchone()[0] + 1:04d}"


async def run_knowledge(
    incident_id: str,
    ci_class: str,
    verification_status: str,
    failure_signature: str | None = None,
    attempted_fix: str | None = None,
) -> SpecialistResult:
    tracker = TurnTracker("knowledge")
    tracker.use_turn()

    negative_kb_entry = None
    if verification_status == "symptom_suppressed":
        # Scoped to CI class + failure signature (domain-guardrails.md bias mitigation table:
        # "Negative-KB overcorrection" — never a blanket filter).
        conn = sqlite3.connect(DB_PATH)
        try:
            entry_id = _next_negkb_id(conn)
            conn.execute(
                "INSERT INTO negative_kb_entries (id, ci_class, failure_signature, attempted_fix, reason_failed, source_incident_id) VALUES (?,?,?,?,?,?)",
                (entry_id, ci_class, failure_signature or "unspecified", attempted_fix or "unspecified",
                 "alert cleared but health probe did not recover through the stabilisation window", incident_id),
            )
            conn.commit()
            negative_kb_entry = {"id": entry_id, "ci_class": ci_class, "failure_signature": failure_signature}
        finally:
            conn.close()

    return SpecialistResult(
        agent_name="knowledge", incident_id=incident_id,
        result={"verification_status": verification_status, "negative_kb_entry": negative_kb_entry},
        cited_artifact_ids=[], confidence=1.0,
        turns_used=tracker.turns_used, termination_reason="knowledge_capture_complete",
    )
