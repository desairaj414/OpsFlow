"""Creates the SQLite DB from schema.sql and populates the tables that have Phase 1 generated
data (cmdb_ci, cmdb_relationship, cmdb_ci_ground_truth, alerts, negative_kb_entries, runbooks).
Everything else (incidents, evidence, hypotheses, plans, approvals, ...) is created empty — those
fill in at runtime once agents exist (Phase 3+), not from static generated data.

    python db/init_db.py         # (re)creates data/app.db
    python db/init_db.py --test  # also runs population + row-count self-checks
"""
import json
import os
import sqlite3
import sys

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
        "INSERT OR REPLACE INTO cmdb_ci (id, name, type, owner, environment, criticality, patch_level, last_verified_at) VALUES (?,?,?,?,?,?,?,?)",
        [(c["id"], c["name"], c["type"], c["owner"], c["environment"], c["criticality"], c["patch_level"], c["last_verified_at"]) for c in cmdb["cis"]],
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
        "INSERT OR REPLACE INTO alerts (id, source, raw_payload, received_at, modality) VALUES (?,?,?,?,?)",
        [(a["id"], a["source"], json.dumps(a["raw_payload"]), a["received_at"], "http") for a in alerts],
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
        populate_pii_ground_truth(conn)
        populate_scenarios(conn)
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
                  "audit_log", "autonomy_ladder", "scenarios", "model_call_cache", "pii_ground_truth"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cur.fetchone()[0]
    conn.close()

    print("\nRow counts:", counts)
    assert counts["cmdb_ci"] == 200
    assert counts["cmdb_relationship"] > 0
    assert counts["cmdb_ci_ground_truth"] == 200
    assert counts["alerts"] == 500
    assert counts["negative_kb_entries"] == 40
    assert counts["runbooks"] == 22
    assert counts["pii_ground_truth"] == 31
    assert counts["scenarios"] == 6  # Phase 5 step 1: SCEN-01..06 (non-edge-case); step 2 adds edge cases on top
    empty_expected = ["incidents", "evidence", "hypotheses", "plans", "approvals", "verification_results",
                       "audit_log", "autonomy_ladder", "model_call_cache"]
    assert all(counts[t] == 0 for t in empty_expected), "a table meant to be runtime-only has pre-seeded rows"
    print("\nSELF-TEST PASSED: all 17 tables created, populated tables have correct volumes, runtime-only tables correctly empty.")
