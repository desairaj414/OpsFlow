"""Append-only audit log write path, per schema-db.md `audit_log` (domain-privacy.md "Immutable
audit trail"). Deliberately exposes ONLY an insert function — there is no update/delete function
anywhere in this module, by design, not by convention. Every write captures actor, action, target,
timestamp, evidence IDs, model used, approval reference, and input modality.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(REPO_ROOT, "data", "app.db")


def write_audit_entry(
    conn: sqlite3.Connection,
    actor: str,
    action: str,
    target_artifact: str | None = None,
    evidence_ids: list[str] | None = None,
    model_used: str | None = None,
    approval_ref: str | None = None,
    input_modality: str | None = None,
) -> int:
    """The only write path into audit_log. Always an INSERT — never touches an existing row."""
    cur = conn.execute(
        "INSERT INTO audit_log (actor, action, target_artifact, timestamp, evidence_ids, model_used, approval_ref, input_modality) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            actor, action, target_artifact,
            datetime.now(timezone.utc).isoformat(),
            json.dumps(evidence_ids or []),
            model_used, approval_ref, input_modality,
        ),
    )
    conn.commit()
    return cur.lastrowid


def read_audit_log(conn: sqlite3.Connection, actor: str | None = None, target_artifact: str | None = None) -> list[dict]:
    """Read-only view — the only other function this module exposes."""
    query = "SELECT id, actor, action, target_artifact, timestamp, evidence_ids, model_used, approval_ref, input_modality FROM audit_log"
    clauses, params = [], []
    if actor:
        clauses.append("actor = ?")
        params.append(actor)
    if target_artifact:
        clauses.append("target_artifact = ?")
        params.append(target_artifact)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id"
    cur = conn.execute(query, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
