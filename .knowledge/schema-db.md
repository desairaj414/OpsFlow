---
type: schema
title: Database Schema (SQLite + Chroma)
status: active
updated: 2026-08-07
related: [api-contract.md, prd-phase-1.md, domain-workflows.md]
---

**Not specified verbatim in PRD_FINAL.md — this is the operational detail an execution session
needs, derived from PRD §1.4/§2.4/§3.5/§3.6/§6/§7 without changing any product decision. Frozen
2026-08-07 — the `cmdb_ci`/`cmdb_ci_ground_truth`/`cmdb_relationship` shapes below match what
`backend/data_gen/cmdb.py` actually generates; `alerts` here is the table ingested alerts land in
after normalisation, distinct from the raw heterogeneous shapes the Monitoring simulator serves
(see `backend/data_gen/alerts.py` / `mcp_servers/simulators/monitoring.py`) — those two are not
the same table and should not be conflated.**

## SQLite — transactional/state (PRD §3.5 storage split)
- `cmdb_ci` — as-recorded CI state: id, name, type, owner, environment, criticality, patch_level, last_verified_at, relationships (adjacency table `cmdb_relationship(ci_id, related_ci_id, relation_type)`).
- `cmdb_ci_ground_truth` — same shape, the "actual" state (~35% deliberately diverges) for the Drift-vs-Truth screen.
- `alerts` — raw ingested alerts: id, source, raw_payload, received_at, modality (`http`/inferred).
- `incidents` — `MaintenanceSignal`-derived unified record: id, workflow_type (`incident`|`patch`|`performance`), status, priority (recomputed, not vendor-anchored), linked_alert_ids, linked_ci_ids, created_via_modality (`alert`|`voice`|`image`).
- `evidence` — artifact_id (e.g. `ALERT-1043`, `CI-0087`, `IMG-nnn`), incident_id, source_type, extract, confidence.
- `hypotheses` — incident_id, text, confidence, cited_artifact_ids (must be non-empty — see [domain-guardrails.md](domain-guardrails.md)).
- `plans` — incident_id, runbook_id, steps (bounded to runbook catalog only), blast_radius, policy_gate_result.
- `approvals` — plan_id, decision (`approve`|`edit`|`reject`), reason, actor, modality (incl. `voice`), timestamp.
- `verification_results` — incident_id, alert_cleared (bool), health_probe_recovered (bool), status (`verified_resolved`|`symptom_suppressed`), stabilisation_window_end.
- `audit_log` — append-only: actor, action, target_artifact, timestamp, evidence_ids, model_used, approval_ref, input_modality. Never updated, only inserted.
- `autonomy_ladder` — runbook_id, current_tier, verified_resolution_count, last_promoted_at.
- `negative_kb_entries` — ci_class, failure_signature, attempted_fix, reason_failed, source_incident_id.
- `runbooks` — id, class (`remediation`|`patching`|`tuning`), declared_human_step_count, content_ref (points at chunked Chroma doc).
- `scenarios` — id, name, workflow_type, is_edge_case (bool), fixture_path — the Scenario Library, doubles as the test suite (PRD §6.1/§5 Phase 5).
- `model_call_cache` — hash(prompt_version, scrubbed_input) → response, tokens, latency, model — see [arch-overview.md](arch-overview.md) caching strategy.
- `pii_ground_truth` — planted sensitive items + location, for computing scrubber precision/recall (PRD §6.2).

## Chroma — vector/RAG (PRD §3.5)
- Collection `runbooks` — chunked per the structural rules in [domain-guardrails.md](domain-guardrails.md) §chunking, metadata includes heading path (`Runbook 14 › Rollback › Step 3`).
- Collection `postmortems` — narrative RCA docs.
- Collection `ticket_history` — closed incidents/changes/tuning tasks, embedded for retrieval.
- Collection `negative_kb` — embedded separately from positive knowledge, consulted at planning time, scoped by CI class + failure signature (never a blanket filter — see bias mitigation in [domain-guardrails.md](domain-guardrails.md)).

## Why SQLite + Chroma, not Postgres/Neo4j (do not re-decide)
See [decisions-log.md](decisions-log.md) — moderate data volume (hundreds of records), CI
relationships covered by an adjacency table.
