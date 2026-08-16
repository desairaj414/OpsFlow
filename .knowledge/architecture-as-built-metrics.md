---
type: reference
title: Architecture As-Built — Overview Tab Metrics
status: active
updated: 2026-08-16
related: [architecture-as-built.md, arch-overview.md, api-contract.md]
---

Split out of [architecture-as-built.md](architecture-as-built.md) (2026-08-16, file exceeded ~200
lines) — that node covers the multi-agent flow; this one covers every Overview-tab number,
file-by-file/computation-by-computation. Update this node (not arch-overview.md) if the
implementation changes.

## Overview tab, every metric

Overview.jsx fetches 4 endpoints on load: `GET /metrics/summary`, `GET /cmdb/drift`,
`GET /autonomy-ladder`, `GET /audit-log?limit=6`. All numbers are computed **live, on every page
load**, from real SQLite `audit_log`/`negative_kb_entries`/`cmdb_ci*`/`autonomy_ladder` rows and
the real `data/alerts.json` dataset — nothing on this tab is a canned/mocked number.

### CMDB drift, explained plainly (feeds "CMDB drift rate" + "CMDB accuracy" below)
Two datasets, generated identical, then deliberately pulled apart: `data/cmdb.json` (→ `cmdb_ci`
table) is the **"recorded"** value (what the CMDB officially says); `data/cmdb_ground_truth.json`
(→ `cmdb_ci_ground_truth`) is the **"actual"** value (what you'd find if you actually checked the
real system). At generation time (`data_gen/cmdb.py`, fixed seed), **35% of the 200 CIs** (~70) each
get **exactly one** of `patch_level`/`criticality`/`environment`/`owner` changed to something else
— e.g. CI-0056 recorded as `patch_level "4.20.4"` but ground-truth `"6.13.7"`, everything else about
it identical. `GET /cmdb/drift` compares 6 fields per CI (those 4, plus `name`/`last_verified_at`,
which never actually diverge in this dataset) — any mismatch flags that CI "drifted."
`drift_rate = drifted_count / total_cis` (e.g. 70/200 = 35%); the accuracy donut is the same split
shown as counts. **This never changes during a live session** — confirmed the Sync agent's
`propose_ci_update` deliberately does NOT mutate the CI record (logs a pending proposal only, a
documented human-approval gate with no "apply" step built yet), so resolving incidents doesn't
shift these numbers. It's a static snapshot of CMDB messiness, not a live metric.

### Top KPI row (7 tiles)
| Tile | Source | Computation |
|---|---|---|
| **Workflow runs this session** | `metrics.total_workflow_runs_this_session` | `COUNT(audit_log)` where `action='correlate'` — one row per real `run_workflow` call this session |
| **Completed** | `metrics.completed_runs` | `COUNT(audit_log)` where `action='execute_plan'` — reached execution, i.e. wasn't blocked/stopped/still-pending. **Note**: this does NOT mean "verified fixed" — a `symptom_suppressed` outcome still counts as "Completed" here, since it did execute. Verified-vs-suppressed isn't broken out on this tile. |
| **Human approvals** | `metrics.human_approvals` | `COUNT(audit_log)` where `action='human_approve_plan'` (via `/workflows/decision` or the chat's `approve_incident`) |
| **CMDB drift rate** | `drift.drift_rate` | `drifted_count / total_cis`, rounded to 3dp, shown as % — from `GET /cmdb/drift` diffing `cmdb_ci` (recorded) vs `cmdb_ci_ground_truth` field-by-field |
| **Stopped before completion** | `metrics.stopped_before_completion` | `total_workflow_runs_this_session - completed_runs` — runs that started but never reached `execute_plan` (enrichment failure, no valid hypothesis, policy-blocked, no valid runbook, or still sitting in `pending_approval`) |
| **Negative-KB entries seeded** | `metrics.negative_kb_entries_seeded` | `COUNT(*)` on `negative_kb_entries` — includes both the Phase-1 seed data AND any real entries the Knowledge agent added this session on a `symptom_suppressed` outcome |
| **Manual steps avoided** | `metrics.manual_steps_avoided` | Sum of `len(evidence_ids)` across every `execute_plan` audit row — `evidence_ids` there is the real list of runbook step-chunk IDs that specific plan executed, so this is a real count, not an estimate |

### Chart row 1 (3 cards)
| Card | Source | Computation |
|---|---|---|
| **Human decisions** (bar) | `human_approvals` vs `metrics.human_rejections` | `human_rejections = COUNT(audit_log)` where `action='human_reject_plan'` |
| **Manual triage avoided** ("alerts collapsed" gauge) | `metrics.correlation_noise_reduction_ratio` | `round(1 - n_clusters/len(alerts), 3)` — runs DBSCAN correlation (see architecture-as-built.md's Correlate section) over **every** alert in `data/alerts.json` (the full synthetic dataset, not just this session's), counts distinct `cluster_id`s. E.g. 200 alerts → 196 clusters = ~2% collapsed. This is the metric's only live consumer today. |
| **CMDB accuracy** (donut) | `drift.total_cis - drift.drifted_count` (Accurate) vs `drift.drifted_count` (Drifted) | Same drift diff as the KPI tile, shown as counts instead of a rate |

### Chart row 2 (3 cards)
| Card | Source | Computation |
|---|---|---|
| **Incident resolution time** (stat pair) | `avg_signal_to_plan_seconds`, `avg_signal_to_verified_resolution_seconds` | `_compute_resolution_timing()`: per `incident_id`, takes the real timestamp of its first `correlate` audit row as t0, first `draft_plan` row as t_plan, first `verify_resolution` row as t_verified; averages `(t_plan - t0)` and `(t_verified - t0)` in seconds across all incidents that reached each stage. Sublabels show how many incidents contributed to each average. Real wall-clock, not simulated. |
| **Human satisfaction (proxy)** (gauge) | `metrics.approval_rate_satisfaction_proxy` | `human_approvals / (human_approvals + human_rejections)`. Shown as "no decisions yet" (not a misleading 0%) when both are zero. |
| **Toil removed** | `metrics.manual_steps_avoided` | Identical number to the "Manual steps avoided" KPI tile, shown as a large standalone figure |

### Bottom row (2 cards)
| Card | Source | Computation |
|---|---|---|
| **Recent activity** | `GET /audit-log?limit=6` | Last 6 rows from `audit_log`, newest first. Server-side role-gated to approver/admin (`require_role`); an ops_engineer sees "Sign in as Approver or Admin..." instead, since the endpoint 403s and the frontend maps that to `entries: null`. |
| **Most-trusted runbooks** | `GET /autonomy-ladder`, top 5 by `verified_resolution_count` | Joins `autonomy_ladder` + `runbooks` tables. `db/init_db.py::populate_autonomy_ladder()` seeds one row per runbook at `current_tier='suggest_only'`, `verified_resolution_count=0` (added 2026-08-08 — the table previously had zero seed rows and no writer at all, so this card and the Autonomy Ladder tab were permanently blank; not a bug, just never seeded). `verified_resolution_count`/`current_tier` still have no runtime writer anywhere — this card reflects **static seed data**, not live promotions during the session, consistent with the Autonomy Ladder tab's own "no runbook has been promoted yet in this session" framing. |
