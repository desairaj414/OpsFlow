"""Creates the SQLite DB from schema.sql and populates the tables that have Phase 1 generated
data (cmdb_ci, cmdb_relationship, cmdb_ci_ground_truth, alerts, negative_kb_entries, runbooks),
plus local_tickets' large ServiceNow+Jira historical backlog (pre-session data — see
populate_local_tickets_bulk). Everything else (incidents, evidence, hypotheses, plans, approvals,
...) is created empty — those fill in at runtime once agents exist (Phase 3+), not from static
generated data.

    python db/init_db.py         # (re)creates data/app.db
    python db/init_db.py --test  # also runs population + row-count self-checks
"""
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

# Lets `python db/init_db.py` (run with backend/db/ as sys.path[0]) import auth_utils.py, which
# lives one level up in backend/ — same pattern as db/load_chroma.py's `import chunking`.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def create_schema(conn: sqlite3.Connection) -> None:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())


def populate_cmdb(conn: sqlite3.Connection) -> None:
    with open(os.path.join(DATA_DIR, "cmdb.json"), encoding="utf-8") as f:
        cmdb = json.load(f)
    conn.executemany(
        "INSERT OR REPLACE INTO cmdb_ci (id, name, display_name, type, owner, environment, criticality, patch_level, last_verified_at) VALUES (?,?,?,?,?,?,?,?,?)",
        [(c["id"], c["name"], c.get("display_name", c["name"]), c["type"], c["owner"], c["environment"], c["criticality"], c["patch_level"], c["last_verified_at"]) for c in cmdb["cis"]],
    )
    conn.executemany(
        "INSERT INTO cmdb_relationship (ci_id, related_ci_id, relation_type) VALUES (?,?,?)",
        [(r["ci_id"], r["related_ci_id"], r["relation_type"]) for r in cmdb["relationships"]],
    )

    with open(os.path.join(DATA_DIR, "cmdb_ground_truth.json"), encoding="utf-8") as f:
        ground_truth = json.load(f)
    conn.executemany(
        "INSERT OR REPLACE INTO cmdb_ci_ground_truth (id, name, type, owner, environment, criticality, patch_level, last_verified_at) VALUES (?,?,?,?,?,?,?,?)",
        # _diverged_field is a dev-only marker (added by data_gen/cmdb.py) — stripped here, never persisted.
        [(g["id"], g["name"], g["type"], g["owner"], g["environment"], g["criticality"], g["patch_level"], g["last_verified_at"]) for g in ground_truth],
    )


def populate_alerts(conn: sqlite3.Connection) -> None:
    """Loads the Monitoring simulator's raw alert stream as ingested rows — this table is the
    post-ingestion record, not the same object as the simulator's raw heterogeneous payload."""
    with open(os.path.join(DATA_DIR, "alerts.json"), encoding="utf-8") as f:
        alerts = json.load(f)
    conn.executemany(
        "INSERT OR REPLACE INTO alerts (id, source, raw_payload, received_at, modality, ci_id, category, severity, summary) VALUES (?,?,?,?,?,?,?,?,?)",
        [(a["id"], a["source"], json.dumps(a["raw_payload"]), a["received_at"], "http", a["ci_id"], a["category"], a["severity"], a["summary"]) for a in alerts],
    )


def populate_negative_kb(conn: sqlite3.Connection) -> None:
    with open(os.path.join(DATA_DIR, "failed_remediations.json"), encoding="utf-8") as f:
        entries = json.load(f)
    conn.executemany(
        "INSERT OR REPLACE INTO negative_kb_entries (id, ci_class, failure_signature, attempted_fix, reason_failed, source_incident_id) VALUES (?,?,?,?,?,?)",
        [(e["id"], e["ci_class"], e["failure_signature"], e["attempted_fix"], e["reason_failed"], e["source_incident_id"]) for e in entries],
    )


def populate_pii_ground_truth(conn: sqlite3.Connection) -> None:
    path = os.path.join(DATA_DIR, "pii_ground_truth.json")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        snippets = json.load(f)
    rows = []
    for snippet in snippets:
        for item in snippet["planted_items"]:
            start = snippet["text"].find(item["value"])
            end = start + len(item["value"]) if start >= 0 else -1
            rows.append((snippet["source_ref"], item["item_type"], f"{start}-{end}"))
    conn.executemany("INSERT INTO pii_ground_truth (source_ref, item_type, location) VALUES (?,?,?)", rows)


def populate_scenarios(conn: sqlite3.Connection) -> None:
    """Loads the Scenario Library (Phase 5) — each data/scenarios/*.json fixture becomes one row,
    referencing its own file as fixture_path so the eval harness can re-open it for CI/alert/expected
    fields without touching this table's schema."""
    scenarios_dir = os.path.join(DATA_DIR, "scenarios")
    rows = []
    for fname in sorted(os.listdir(scenarios_dir)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(scenarios_dir, fname), encoding="utf-8") as f:
            scenario = json.load(f)
        rows.append((scenario["id"], scenario["name"], scenario["workflow_type"],
                      int(scenario["is_edge_case"]), f"scenarios/{fname}"))
    conn.executemany(
        "INSERT OR REPLACE INTO scenarios (id, name, workflow_type, is_edge_case, fixture_path) VALUES (?,?,?,?,?)",
        rows,
    )


# Demo credentials — seeded so there's a real, working account per role on first run. An admin can
# add more via POST /users at runtime. These are printed by --test below so they're never silently
# hidden in a file the operator has to go dig up.
_DEFAULT_USERS = [
    ("USR-001", "alex.chen", "OpsEngineer!123", "Alex Chen", "ops_engineer"),
    ("USR-002", "priya.sharma", "Approver!123", "Priya Sharma", "approver"),
    ("USR-003", "admin", "Admin!123", "Admin", "admin"),
]


def populate_users(conn: sqlite3.Connection) -> None:
    from auth_utils import hash_password

    now = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        "INSERT OR REPLACE INTO users (id, username, password_hash, display_name, role, created_at) VALUES (?,?,?,?,?,?)",
        [(uid, username, hash_password(pw), display_name, role, now) for uid, username, pw, display_name, role in _DEFAULT_USERS],
    )


def populate_runbooks(conn: sqlite3.Connection) -> None:
    runbooks_dir = os.path.join(DATA_DIR, "runbooks")
    rows = []
    for fname in sorted(os.listdir(runbooks_dir)):
        if not fname.endswith(".md"):
            continue
        with open(os.path.join(runbooks_dir, fname), encoding="utf-8") as f:
            content = f.read()
        rb_id = fname[:-3]
        rb_class = next(line.split(":", 1)[1].strip() for line in content.splitlines() if line.startswith("class:"))
        step_count = int(next(line.split(":", 1)[1].strip() for line in content.splitlines() if line.startswith("declared_human_step_count:")))
        rows.append((rb_id, rb_class, step_count, f"runbooks/{fname}"))
    conn.executemany("INSERT OR REPLACE INTO runbooks (id, class, declared_human_step_count, content_ref) VALUES (?,?,?,?)", rows)


def populate_autonomy_ladder(conn: sqlite3.Connection) -> None:
    """One row per runbook, all starting at the base tier with zero verified resolutions — without
    this the Autonomy Ladder tab and Overview's "Most-trusted runbooks" card have nothing to read
    (the table has no other writer; there is no live promotion engine, PRD §4.0 scope cut). Seeding
    the starting state is not the same as building promotion logic — `current_tier`/
    `verified_resolution_count` still never change at runtime."""
    runbook_ids = [r[0] for r in conn.execute("SELECT id FROM runbooks").fetchall()]
    conn.executemany(
        "INSERT OR REPLACE INTO autonomy_ladder (runbook_id, current_tier, verified_resolution_count, last_promoted_at) VALUES (?, 'suggest_only', 0, NULL)",
        [(rb_id,) for rb_id in runbook_ids],
    )


def populate_integration_settings(conn: sqlite3.Connection) -> None:
    """Single row, all null until an admin sets a real instance URL (GET/POST /config/integrations)
    — seeded here purely so the endpoint always has a row to read/update, never a functional sync."""
    conn.execute("INSERT OR REPLACE INTO integration_settings (id, servicenow_instance_url, jira_instance_url, last_synced_at) VALUES (1, NULL, NULL, NULL)")


def populate_patch_inventory(conn: sqlite3.Connection) -> None:
    with open(os.path.join(DATA_DIR, "patch_inventory.json"), encoding="utf-8") as f:
        patches = json.load(f)
    conn.executemany(
        "INSERT OR REPLACE INTO patch_inventory (id, ci_id, vendor, title, severity, cve_ids, released_at, sla_days, depends_on_patch_ids, status) VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(p["id"], p["ci_id"], p["vendor"], p["title"], p["severity"], json.dumps(p["cve_ids"]),
          p["released_at"], p["sla_days"], json.dumps(p["depends_on_patch_ids"]), p["status"]) for p in patches],
    )


def populate_change_calendar(conn: sqlite3.Connection) -> None:
    with open(os.path.join(DATA_DIR, "change_calendar.json"), encoding="utf-8") as f:
        calendar = json.load(f)
    conn.executemany(
        "INSERT OR REPLACE INTO change_calendar (id, scope, starts_at, ends_at, reason) VALUES (?,?,?,?,?)",
        [(w["id"], w["scope"], w["starts_at"], w["ends_at"], w["reason"]) for w in calendar],
    )


SYSTEM_LABEL = {"itsm": "ServiceNow", "tracker": "Jira"}


def populate_local_tickets_bulk(conn: sqlite3.Connection) -> None:
    """Seeds local_tickets with a large historical backlog across BOTH systems — ServiceNow
    ('itsm') and Jira ('tracker') — from data/local_tickets_seed.json
    (data_gen/local_tickets_bulk.py, 2000 rows per system, evenly split across
    incident/patch/performance). Historical/pre-session data, deliberately decoupled from
    tickets.csv (which feeds the real gateway-embedded ticket_history Chroma collection — scaling
    that to thousands of rows would mean thousands of real embedding calls for data whose only job
    is populating the Tickets tab). Without this, system='tracker' rows in particular were
    permanently absent on a fresh DB: no live code path ever creates one (main.py's
    _persist_ticket_snapshot deliberately only writes 'itsm' rows from a real run — an
    alert-driven diagnosis raises exactly one ServiceNow ticket, never also a Jira issue, see its
    own comment). trace_snapshot's placeholder carries the ticket's own display fields (ci_id,
    external_id, summary, priority, dates) alongside the empty trace — CockpitShell's openTicket()
    only ever passes trace_snapshot through to Incident Workspace, discarding the outer ticket row,
    so without this the historical-ticket view IncidentWorkspace.jsx renders for status="historical"
    would have nothing real to show either. See errors-solved.md: originally shipped with a bare
    placeholder, which rendered as six empty "not reached" cards on every one of these 4000
    tickets — technically not broken, but read as broken."""
    path = os.path.join(DATA_DIR, "local_tickets_seed.json")
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        "INSERT INTO local_tickets (system, external_id, cmdb_ci, workflow_type, status_raw, status_normalized, "
        "priority, summary, opened_at, closed_at, linked_incident_id, trace_snapshot, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                r["system"], r["external_id"], r["cmdb_ci"], r["workflow_type"], r["status_raw"], r["status_normalized"],
                r["priority"], r["summary"], r["opened_at"], r["closed_at"], None,
                json.dumps({
                    "incident_id": None, "modality": "alert", "workflow_type": r["workflow_type"], "status": "historical",
                    "ci_id": r["cmdb_ci"], "external_id": r["external_id"], "system": r["system"],
                    "summary": r["summary"], "priority": r["priority"], "status_label": r["status_normalized"],
                    "opened_at": r["opened_at"], "closed_at": r["closed_at"],
                    "reason": f"Imported {SYSTEM_LABEL[r['system']]} backlog item — pre-dates this session, "
                              "never run through the agent chain.",
                    "verification_status": None, "trace": [], "agent_card": None,
                }),
                now,
            )
            for r in rows
        ],
    )


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)  # rebuild clean each run — this is generated/derived data, safe to drop
    conn = sqlite3.connect(DB_PATH)
    try:
        create_schema(conn)
        populate_cmdb(conn)
        populate_alerts(conn)
        populate_negative_kb(conn)
        populate_runbooks(conn)
        populate_autonomy_ladder(conn)
        populate_pii_ground_truth(conn)
        populate_scenarios(conn)
        populate_users(conn)
        populate_integration_settings(conn)
        populate_patch_inventory(conn)
        populate_change_calendar(conn)
        populate_local_tickets_bulk(conn)
        conn.commit()
    finally:
        conn.close()
    print(f"{DB_PATH} created and populated.")


if __name__ == "__main__":
    main()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    counts = {}
    for table in ["cmdb_ci", "cmdb_relationship", "cmdb_ci_ground_truth", "alerts", "negative_kb_entries", "runbooks",
                  "incidents", "evidence", "hypotheses", "plans", "approvals", "verification_results",
                  "audit_log", "autonomy_ladder", "scenarios", "model_call_cache", "pii_ground_truth", "users",
                  "local_tickets", "integration_settings", "patch_inventory", "change_calendar"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cur.fetchone()[0]
    conn.close()

    print("\nRow counts:", counts)
    assert counts["cmdb_ci"] == 200
    assert counts["cmdb_relationship"] > 0
    assert counts["cmdb_ci_ground_truth"] == 200
    assert counts["alerts"] == 500
    assert counts["negative_kb_entries"] == 500  # fixed seed, data_gen/negative_kb.py
    assert counts["runbooks"] == 22
    assert counts["pii_ground_truth"] == 31
    assert counts["scenarios"] == 14  # 10 non-edge (SCEN-01..10) + 4 edge cases (edge_*.json)
    assert counts["users"] == 3  # default seed: one real account per role; admin can add more via POST /users
    assert counts["integration_settings"] == 1  # single seeded row, all null until a real instance is set
    assert counts["patch_inventory"] == 153  # fixed seed, data_gen/patch_inventory.py
    assert counts["change_calendar"] == 12  # fixed seed, data_gen/patch_inventory.py
    assert counts["autonomy_ladder"] == counts["runbooks"]  # one starting-tier row per runbook, no live writer beyond seed
    assert counts["local_tickets"] == 4000  # 2000 itsm + 2000 tracker, fixed seed, data_gen/local_tickets_bulk.py
    empty_expected = ["incidents", "evidence", "hypotheses", "plans", "approvals", "verification_results",
                       "audit_log", "model_call_cache"]
    assert all(counts[t] == 0 for t in empty_expected), "a table meant to be runtime-only has pre-seeded rows"
    print(f"\nSELF-TEST PASSED: all {len(counts)} tables created, populated tables have correct volumes, runtime-only tables correctly empty.")
    print("\nDemo login credentials (username / password):")
    for _uid, username, pw, display_name, role in _DEFAULT_USERS:
        print(f"  {username:15s} / {pw:16s}  ({display_name}, {role})")
