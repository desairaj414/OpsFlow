"""Unit tests for the append-only audit log (backend/orchestrator/audit.py)."""
import inspect
import os
import sqlite3

import pytest

import orchestrator.audit as audit_module
from orchestrator.audit import read_audit_log, write_audit_entry

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")


def _fresh_conn() -> sqlite3.Connection:
    """In-memory DB built from the real schema.sql, so these tests exercise the actual
    append-only triggers, not a hand-simplified stand-in table."""
    conn = sqlite3.connect(":memory:")
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    return conn


def test_no_update_or_delete_function_exists_in_module():
    """Append-only by design: the module must not expose any function that could mutate/remove a row."""
    names = [name for name, _ in inspect.getmembers(audit_module, inspect.isfunction)]
    for forbidden in ("update", "delete", "remove", "edit"):
        assert not any(forbidden in n.lower() for n in names), f"found a '{forbidden}'-like function: {names}"


def test_write_entry_captures_all_required_fields():
    conn = _fresh_conn()
    write_audit_entry(
        conn, actor="agent:diagnosis", action="propose_plan", target_artifact="INC-001",
        evidence_ids=["ALERT-0001", "CI-0009"], model_used="azure_ai/genailab-maas-DeepSeek-R1",
        approval_ref="APR-001", input_modality="alert",
    )
    entries = read_audit_log(conn)
    assert len(entries) == 1
    e = entries[0]
    for field in ["actor", "action", "target_artifact", "timestamp", "evidence_ids", "model_used", "approval_ref", "input_modality"]:
        assert e[field] is not None, f"missing {field}"
    assert e["actor"] == "agent:diagnosis"
    assert "ALERT-0001" in e["evidence_ids"]


def test_writes_are_append_only_never_overwrite():
    conn = _fresh_conn()
    id1 = write_audit_entry(conn, actor="a", action="act1")
    id2 = write_audit_entry(conn, actor="a", action="act2")
    assert id1 != id2
    entries = read_audit_log(conn)
    assert len(entries) == 2
    assert entries[0]["action"] == "act1"
    assert entries[1]["action"] == "act2"


def test_db_layer_rejects_update_even_via_raw_sql():
    """The append-only guarantee is enforced by a DB trigger, not just application discipline —
    even a raw SQL UPDATE bypassing this module entirely must be rejected."""
    conn = _fresh_conn()
    write_audit_entry(conn, actor="a", action="act1")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE audit_log SET action = 'tampered' WHERE id = 1")
    entries = read_audit_log(conn)
    assert entries[0]["action"] == "act1"  # unchanged


def test_db_layer_rejects_delete_even_via_raw_sql():
    conn = _fresh_conn()
    write_audit_entry(conn, actor="a", action="act1")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM audit_log WHERE id = 1")
    assert len(read_audit_log(conn)) == 1
