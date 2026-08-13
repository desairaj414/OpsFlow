---
type: Schema
title: Database Schema — SQLite + Chroma
description: Transactional/workflow state lives in SQLite; runbook/postmortem/ticket-history/negative-KB content lives embedded in Chroma. An append-only audit_log is enforced at the DB layer, not just by application discipline.
resource: backend/db/schema.sql
tags: [schema, database, sqlite, chroma]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: schema-sql
    resource: backend/db/schema.sql
    title: backend/db/schema.sql
    last_modified: 2026-08-08
  - id: schema-db
    resource: .knowledge/schema-db.md
    title: Database Schema (SQLite + Chroma)
    last_modified: 2026-08-07
---

# SQLite — transactional/state

| Table | Purpose |
|---|---|
| `cmdb_ci` / `cmdb_ci_ground_truth` | as-recorded vs. actual CI state — the pair the Drift Queue diffs, see [Overview Metrics](/architecture/overview-metrics.md) |
| `cmdb_relationship` | adjacency edges [Blast Radius](/guardrails/blast-radius.md) BFS-walks |
| `alerts` | ingested alerts, normalized (`ci_id`/`category`/`severity`/`summary`) |
| `incidents`, `evidence`, `hypotheses`, `plans`, `approvals`, `verification_results` | per-incident structured record shapes — as of this bundle's writing these have no runtime writer; the agent chain's real state instead flows through `audit_log` and the JSON `trace_snapshot` on `local_tickets` |
| `audit_log` | append-only actor/action/target/evidence/model/approval/modality log — see below |
| `autonomy_ladder` | one row per runbook, seeded at `suggest_only`/0 — no runtime promotion writer exists yet, a display of intended structure, not a live promotion engine |
| `negative_kb_entries` | written by [Knowledge Agent](/agents/knowledge-agent.md) on a `symptom_suppressed` outcome |
| `runbooks` | id/class/content_ref pointing at the chunked Chroma document |
| `scenarios` | the Scenario Library, doubling as the test-fixture set |
| `model_call_cache` | `hash(prompt_version, scrubbed_input) -> response` |
| `pii_ground_truth` | planted sensitive items for the [Scrubber](/guardrails/scrubber.md)'s measured precision/recall |
| `patch_inventory`, `change_calendar` | simulated vendor patch feed + blackout windows, read by `guardrails/scheduling.py` |
| `users` | real accounts — PBKDF2-HMAC-SHA256 salted password hashes, one fixed role per account (`ops_engineer`\|`approver`\|`admin`) — see [Real Authentication](/decisions/real-authentication.md) |
| `local_tickets` | additive local mirror of the (simulated) ITSM/Tracker ticket per workflow run, including a full `trace_snapshot` JSON so a past run can be reopened without re-running the agent chain (there is no checkpointing — see [No Workflow Checkpointing](/decisions/no-workflow-checkpointing.md)) |
| `integration_settings` | single row, holds where a future real ServiceNow/Jira instance would be pointed at — never functional in this build |

[^schema-sql]

# `audit_log` — enforced append-only

```sql
CREATE TRIGGER audit_log_no_update BEFORE UPDATE ON audit_log
BEGIN SELECT RAISE(ABORT, 'audit_log is append-only: UPDATE is not permitted'); END;
```

A real SQLite trigger rejects any `UPDATE`/`DELETE` at the database layer — a raw SQL statement
against this table is rejected by the DB itself, not merely a convention the application layer is
trusted to honor.[^schema-sql] Every workflow step, every human decision, every intake action writes
one row here — actor, action, target artifact, timestamp, evidence IDs, model used, approval
reference, input modality.

# Chroma — vector/RAG

| Collection | Content |
|---|---|
| `runbooks` | chunked per [Chunking](/guardrails/chunking.md)'s structural rules; metadata includes a heading path and `class` |
| `postmortems` | narrative RCA docs, plus Knowledge Base articles tagged `doc_type` in the same chunking function |
| `ticket_history` | closed incidents/changes/tuning tasks, embedded for [Enrichment](/agents/enrichment-agent.md)'s precedent lookup |
| `negative_kb` | embedded separately from positive knowledge, scoped by `(ci_class, failure_signature)`, never a blanket filter |

All four are embedded and queried via a single **fixed** provider — see
[Embeddings Fixed Provider](/decisions/embeddings-fixed-provider.md) — regardless of which LLM
provider a given visitor session is using.

# Why SQLite + Chroma, not Postgres/Neo4j

Moderate data volume (hundreds of records); CI relationships are covered adequately by a plain
adjacency table, so a graph database was judged unnecessary overkill for this scale.[^schema-db]

[^schema-sql]: backend/db/schema.sql
[^schema-db]: Database Schema (SQLite + Chroma)
