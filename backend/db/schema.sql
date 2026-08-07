-- SQLite schema per .knowledge/schema-db.md (frozen 2026-08-07). Transactional/state tables only —
-- vector/RAG content lives in Chroma (see backend/db/load_chroma.py).

CREATE TABLE IF NOT EXISTS cmdb_ci (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    owner TEXT NOT NULL,
    environment TEXT NOT NULL,
    criticality TEXT NOT NULL,
    patch_level TEXT NOT NULL,
    last_verified_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cmdb_relationship (
    ci_id TEXT NOT NULL REFERENCES cmdb_ci(id),
    related_ci_id TEXT NOT NULL REFERENCES cmdb_ci(id),
    relation_type TEXT NOT NULL
);

-- Same shape as cmdb_ci — the "actual" state, ~35% deliberately diverges (Drift-vs-Truth screen).
CREATE TABLE IF NOT EXISTS cmdb_ci_ground_truth (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    owner TEXT NOT NULL,
    environment TEXT NOT NULL,
    criticality TEXT NOT NULL,
    patch_level TEXT NOT NULL,
    last_verified_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    raw_payload TEXT NOT NULL,
    received_at TEXT NOT NULL,
    modality TEXT NOT NULL DEFAULT 'http'
);

CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    workflow_type TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT NOT NULL,
    linked_alert_ids TEXT,
    linked_ci_ids TEXT,
    created_via_modality TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
    artifact_id TEXT PRIMARY KEY,
    incident_id TEXT REFERENCES incidents(id),
    source_type TEXT NOT NULL,
    extract TEXT NOT NULL,
    confidence REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS hypotheses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT REFERENCES incidents(id),
    text TEXT NOT NULL,
    confidence REAL NOT NULL,
    cited_artifact_ids TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT REFERENCES incidents(id),
    runbook_id TEXT REFERENCES runbooks(id),
    steps TEXT NOT NULL,
    blast_radius TEXT,
    policy_gate_result TEXT
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER REFERENCES plans(id),
    decision TEXT NOT NULL,
    reason TEXT,
    actor TEXT NOT NULL,
    modality TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verification_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT REFERENCES incidents(id),
    alert_cleared INTEGER NOT NULL,
    health_probe_recovered INTEGER NOT NULL,
    status TEXT NOT NULL,
    stabilisation_window_end TEXT
);

-- Append-only audit trail — never updated, only inserted. Enforced at the DB layer below, not
-- just by application discipline: any UPDATE/DELETE attempt aborts with an error.
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target_artifact TEXT,
    timestamp TEXT NOT NULL,
    evidence_ids TEXT,
    model_used TEXT,
    approval_ref TEXT,
    input_modality TEXT
);

CREATE TRIGGER IF NOT EXISTS audit_log_no_update
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only: UPDATE is not permitted');
END;

CREATE TRIGGER IF NOT EXISTS audit_log_no_delete
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only: DELETE is not permitted');
END;

CREATE TABLE IF NOT EXISTS autonomy_ladder (
    runbook_id TEXT PRIMARY KEY REFERENCES runbooks(id),
    current_tier TEXT NOT NULL DEFAULT 'suggest_only',
    verified_resolution_count INTEGER NOT NULL DEFAULT 0,
    last_promoted_at TEXT
);

CREATE TABLE IF NOT EXISTS negative_kb_entries (
    id TEXT PRIMARY KEY,
    ci_class TEXT NOT NULL,
    failure_signature TEXT NOT NULL,
    attempted_fix TEXT NOT NULL,
    reason_failed TEXT NOT NULL,
    source_incident_id TEXT
);

CREATE TABLE IF NOT EXISTS runbooks (
    id TEXT PRIMARY KEY,
    class TEXT NOT NULL,
    declared_human_step_count INTEGER NOT NULL,
    content_ref TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scenarios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    workflow_type TEXT NOT NULL,
    is_edge_case INTEGER NOT NULL DEFAULT 0,
    fixture_path TEXT
);

CREATE TABLE IF NOT EXISTS model_call_cache (
    hash TEXT PRIMARY KEY,
    response TEXT NOT NULL,
    tokens INTEGER,
    latency_ms REAL,
    model TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pii_ground_truth (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_ref TEXT NOT NULL,
    item_type TEXT NOT NULL,
    location TEXT NOT NULL
);
