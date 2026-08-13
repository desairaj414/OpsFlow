---
type: Reference
title: Overview Dashboard Metrics
description: Exactly how every number on the Overview tab is computed and from what real data, so no metric is a canned or estimated figure.
tags: [metrics, dashboard, trust]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-08T00:00:00Z" }
sources:
  - id: architecture-as-built
    resource: .knowledge/architecture-as-built.md
    title: Architecture As-Built
    last_modified: 2026-08-08
---

# Overview

`Overview.jsx` fetches 4 endpoints on load — `GET /metrics/summary`, `GET /cmdb/drift`,
`GET /autonomy-ladder`, `GET /audit-log?limit=6` — and every number is computed **live, on every
page load**, from real SQLite rows (`audit_log`, `negative_kb_entries`, `cmdb_ci*`,
`autonomy_ladder`) and the real `data/alerts.json` dataset. Nothing on this tab is a canned
number.[^architecture-as-built]

# CMDB drift, explained

Two generated-identical, then deliberately-diverged datasets: `cmdb_ci` (the "recorded" CMDB
state) and `cmdb_ci_ground_truth` (the "actual" state — 35% of the 200 CIs each have exactly one
field changed at generation time). `GET /cmdb/drift` field-by-field-compares 6 fields per CI;
`drift_rate = drifted_count / total_cis`. This never changes during a live session — the Sync agent
deliberately never mutates the recorded CI record (only logs a pending proposal), so it's a static
snapshot of CMDB messiness, not a live metric.[^architecture-as-built]

# Top KPI row

| Tile | Computation |
|---|---|
| Workflow runs this session | `COUNT(audit_log)` where `action='correlate'` |
| Completed | `COUNT(audit_log)` where `action='execute_plan'` — reached execution; does **not** mean verified-fixed, a `symptom_suppressed` outcome still counts here |
| Human approvals | `COUNT(audit_log)` where `action='human_approve_plan'` |
| CMDB drift rate | `drifted_count / total_cis`, from the CMDB-drift diff above |
| Stopped before completion | `total_workflow_runs_this_session - completed_runs` |
| Negative-KB entries seeded | `COUNT(*)` on `negative_kb_entries` (seed data + any runtime entries) |
| Manual steps avoided | Sum of `len(evidence_ids)` across every `execute_plan` audit row — a real count of the runbook-step-chunk IDs that plan actually cited, not an estimate |

# Chart rows

| Card | Computation |
|---|---|
| Human decisions (bar) | approvals vs `COUNT(audit_log)` where `action='human_reject_plan'` |
| Manual triage avoided ("alerts collapsed") | `1 - n_clusters/len(alerts)` — runs the real DBSCAN correlation engine over every alert in the full synthetic dataset |
| CMDB accuracy (donut) | same drift diff, shown as counts (accurate vs drifted) instead of a rate |
| Incident resolution time (stat pair) | per-incident real wall-clock: average `(first draft_plan timestamp - first correlate timestamp)` and `(first verify_resolution timestamp - first correlate timestamp)`, across incidents that reached each stage |
| Human satisfaction (proxy, gauge) | `human_approvals / (human_approvals + human_rejections)`; shown as "no decisions yet" rather than a misleading 0% when both are zero |
| Toil removed | identical number to "Manual steps avoided" above, shown as a standalone figure |
| Recent activity | last 6 `audit_log` rows, newest first; role-gated to approver/admin |
| Most-trusted runbooks | top 5 by `verified_resolution_count`, joined from `autonomy_ladder` + `runbooks` — seeded to one starting-tier row per runbook; `verified_resolution_count`/`current_tier` have no runtime writer, so this reflects static seed state, not live promotion during a session |

[^architecture-as-built]: Architecture As-Built
