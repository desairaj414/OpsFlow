-- SQLite schema per .knowledge/schema-db.md (frozen 2026-08-07). Transactional/state tables only —
-- vector/RAG content lives in Chroma (see backend/db/load_chroma.py).

CREATE TABLE IF NOT EXISTS cmdb_ci (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
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
    modality TEXT NOT NULL DEFAULT 'http',
    ci_id TEXT,
    category TEXT,
    severity TEXT,
    summary TEXT
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

-- Real authenticated accounts (decisions-log.md: real-auth decision supersedes the original "no
-- real authentication" PRD call). password_hash is PBKDF2-HMAC-SHA256, salted (auth_utils.py) —
-- never a plaintext password. Role is one of ops_engineer|approver|admin — mapped to
-- guardrails/policy_gate.py's actor_role vocabulary (operator|sre_lead|change_manager) in main.py,
-- not stored here, so the policy gate's frozen/tested vocabulary never has to change.
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pii_ground_truth (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_ref TEXT NOT NULL,
    item_type TEXT NOT NULL,
    location TEXT NOT NULL
);

-- Local record of the ServiceNow/Jira-shaped tickets the (simulated) ITSM/Tracker systems already
-- create per workflow run (supervisor.py/sync.py, untouched by this table — purely additive).
-- Schema-compatible in spirit with a real instance (external_id/system/status mirror the real
-- vendor shapes in mcp_servers/simulators/{itsm,tracker}.py) so a future real-instance swap doesn't
-- need a redesign. trace_snapshot lets a past alert's diagnosis/plan/verification be reopened
-- without re-running the agent chain (decisions-log.md: no checkpointing exists, so this is a
-- point-in-time snapshot, not a resumable state).
CREATE TABLE IF NOT EXISTS local_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    system TEXT NOT NULL,              -- 'itsm' | 'tracker'
    external_id TEXT NOT NULL,         -- sys_id (itsm) or issue key (tracker)
    cmdb_ci TEXT NOT NULL,
    workflow_type TEXT NOT NULL,
    status_raw TEXT NOT NULL,          -- the vendor-shaped state/status as recorded by the simulator
    status_normalized TEXT NOT NULL,   -- 'open' | 'in_progress' | 'resolved' — for the UI
    priority TEXT,
    summary TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    linked_incident_id TEXT,
    trace_snapshot TEXT NOT NULL,      -- JSON: the run's full trace (same shape /workflows/run returns)
    created_at TEXT NOT NULL
);

-- Where a future real ServiceNow/Jira instance would be pointed at — single row, stays null until
-- one exists. Never functional in this build (decisions-log.md); UI shows it as "local simulated
-- data, not yet connected" until instance_url is set by an admin.
CREATE TABLE IF NOT EXISTS integration_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    servicenow_instance_url TEXT,
    jira_instance_url TEXT,
    last_synced_at TEXT
);

-- Patch Management (PRD row 816 / clause C6, data_gen/patch_inventory.py): pending patches per CI
-- as (simulated) vendor patch sites would report them. depends_on_patch_ids is a JSON array of
-- other patch ids (same ci_id) that must apply first — the scheduling rule engine
-- (guardrails/scheduling.py) reads this for dependency-aware grouping.
CREATE TABLE IF NOT EXISTS patch_inventory (
    id TEXT PRIMARY KEY,
    ci_id TEXT NOT NULL REFERENCES cmdb_ci(id),
    vendor TEXT NOT NULL,
    title TEXT NOT NULL,
    severity TEXT NOT NULL,
    cve_ids TEXT,
    released_at TEXT NOT NULL,
    sla_days INTEGER NOT NULL,
    depends_on_patch_ids TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
);

-- Blackout/freeze windows the scheduling rule engine must route maintenance windows around.
-- scope is 'global' | an environment name ('prod'|'staging'|'dev') | a specific ci_id.
CREATE TABLE IF NOT EXISTS change_calendar (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    starts_at TEXT NOT NULL,
    ends_at TEXT NOT NULL,
    reason TEXT NOT NULL
);
