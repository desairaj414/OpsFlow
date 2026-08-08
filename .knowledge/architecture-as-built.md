---
type: reference
title: Architecture As-Built — Agent Chain + Overview Metrics
status: active
updated: 2026-08-08
related: [arch-overview.md, domain-agents.md, models-routing.md, api-contract.md]
---

Companion to [arch-overview.md](arch-overview.md) (which mirrors the frozen PRD design intent —
do not edit it). This node instead documents **what the code actually does today**, file-by-file,
for two things that got asked about directly: the multi-agent flow, and every Overview-tab number.
Update this node (not arch-overview.md) if the implementation changes.

## Part 1 — Multi-agent flow, one agent at a time

Chain order (`orchestrator/supervisor.py::run_workflow`): **Correlate → Enrich → Diagnose → Plan
(+ Policy Gate, computed inside Plan) → Approve (human) → Execute → Verify → Sync → Knowledge**.
Two levels only — Supervisor + specialists, agents never call each other directly. Each specialist
returns a typed `SpecialistResult`, re-validated by the Supervisor before the next dispatch.

### Correlate
**File**: `backend/correlation/cluster.py`, invoked from `backend/main.py`.
**Technique**: classical ML — **scikit-learn `DBSCAN`** clustering over alert timestamps, inside
buckets formed by a deterministic union-find over the CMDB relationship graph (topology group) +
alert category. No LLM.
**Important nuance**: inside a single incident's `run_workflow`, "Correlate" is just an **audit-log
marker** — the Supervisor receives one already-identified alert/CI as input and logs a `correlate`
action; it does not re-run DBSCAN at that moment. The actual DBSCAN computation only runs when
`GET /alerts/correlated` or `GET /metrics/summary` is called — today that means it only really
executes to feed one Overview metric (see Part 2, "Manual triage avoided"). The dedicated
correlated-candidates UI panel that used to also trigger it was removed in this session's Ops
Board redesign.

### Enrich
**File**: `backend/agents/enrichment.py`.
**Technique**: fully deterministic — **no LLM call at all**. Gathers evidence by calling three MCP
tool servers (`cmdb_mcp.get_ci`, `cmdb_mcp.get_relationships`, `monitoring_mcp.get_metric_series`,
and `patch_mcp.*` for patch workflows only), plus **one real RAG/vector-DB lookup**:
`orchestrator/retrieval.py::query_collection("ticket_history", ...)` — embeds the query via the
gateway's `text-embedding-3-large`, does a Chroma similarity search, returns the top-2 nearest past
tickets as "precedent" evidence (each tagged with a confidence derived from vector distance).
Every fact gathered gets a stable `artifact_id` so later agents can cite it by ID rather than
re-stating it.

### Diagnose
**File**: `backend/agents/diagnosis.py`, invoked via `backend/a2a/client.py` → `backend/a2a/endpoint.py`.
**Technique**: **LLM — DeepSeek R1** (`azure_ai/genailab-maas-DeepSeek-R1`), the one step in the
whole chain that goes over the **A2A protocol** (in-process ASGI transport in this build) instead
of a plain in-process function call — the deliberate "one real agent-to-agent handoff" the PRD
scoped. Prompted with the evidence bundle (IDs + short extracts only, never full documents) to
generate 2-4 ranked root-cause hypotheses as JSON. **Citation enforcement**: any hypothesis with an
empty `cited_artifact_ids` or one citing an ID outside the actual evidence bundle is dropped before
it's ever returned — a model can't silently "invent" a fact.

### Plan
**File**: `backend/agents/planner.py`.
**Technique**: **RAG + LLM**, then deterministic guardrails. First does a real Chroma vector search
— `query_collection("runbooks", query_text, where={"class": runbook_class})` — restricted to the
runbook class this workflow type needs, retrieving up to 4 chunks (each chunk = one atomic
numbered runbook step, see Chunking below). Then calls **`gpt-4.1-nano`**
(`azure/genailab-maas-gpt-4.1-nano` — the human-approved substitute after DeepSeek V3 was confirmed
unreachable) to draft a plan **using only those retrieved chunks**; any step citing a chunk ID that
wasn't actually retrieved is dropped (same runbook-bounded-action-space rule as Diagnose's citation
enforcement). After the LLM returns, three things are computed **purely deterministically, never by
the model**: `blast_radius` (`guardrails/blast_radius.py`), `policy_gate_result`
(`guardrails/policy_gate.py` — the thresholds you asked about earlier), and, for patch workflows
only, `maintenance_window` (`guardrails/scheduling.py`).

### Policy Gate
Not a separate agent — computed *inside* Plan's step, described above. Purely rule-based
(threshold comparisons), no LLM, no ML.

### Approve
A human decision point, not code. `run_workflow` returns `status: "pending_approval"` and pauses
unless `auto_approve=True` was explicitly passed (demo/scenario convenience). The decision is made
either in Incident Workspace's `ApprovalSection` or via the chat assistant's `approve_incident`/
`reject_incident` intent (see Chat Assistant below) — both paths write the identical audit entry
and reuse the identical re-run mechanism.

### Execute
Supervisor-internal (`run_workflow`) — just writes an `execute_plan` audit entry (with the executed
step IDs as `evidence_ids`). No LLM, no real script execution against live infrastructure by
design: the "world" being acted on is the seeded metric CSVs from Phase 1, which already contain a
genuine degradation curve for CIs meant to still be broken — that's what lets Verify tell a real
fix from a fake one on real numbers, not a scripted outcome.

### Verify
**File**: `backend/agents/verification.py` — the **Fake Fix Detector**. Fully deterministic, no
LLM. Requires **two independent signals**: the alert cleared, AND the metric series (real CSV data
per CI) recovered and **held** through a stabilisation window (checks the tail 30% of the series
stays under threshold, not just one data point). If only the alert cleared, the outcome is
`symptom_suppressed` (incident stays open) rather than trusted as a real fix.

### Sync
**File**: `backend/agents/sync.py`. Fully deterministic, no LLM. Writes the outcome back to the
simulated ITSM system (`itsm_mcp.add_work_note` + `update_ticket`), and if verified-resolved,
proposes a CMDB field update (`cmdb_mcp.propose_ci_update`) — one consistent record across systems.

### Knowledge
**File**: `backend/agents/knowledge.py`. Fully deterministic, no LLM. Only acts on
`symptom_suppressed` outcomes: seeds a **Negative KB** entry scoped to `(ci_class,
failure_signature)` so a remediation that failed once is remembered and can be checked against
next time — deliberately scoped narrow, never a blanket filter (bias-mitigation table,
domain-guardrails.md).

### Supporting technique — Chunking (not an agent, feeds Enrich/Plan's RAG)
**File**: `backend/chunking.py`. Splits runbooks **only on structural boundaries**
(`### Step N` headings) and postmortems/KB articles on `## Heading` boundaries — never on a
character/token count, so a numbered step is never split mid-instruction. Runbook steps inherit
the document's Prerequisites block ("preamble inheritance") so a retrieved step never loses an
"only if X" condition. This is what populates the Chroma `runbooks` collection Plan queries and the
`ticket_history`/postmortem collections Enrich queries.

### Cross-cutting techniques — not pipeline steps, wrap around the chain
- **Local SLM (Ollama, `llama-3.2-3b-it`) — PII/secret name scrubbing.** `backend/guardrails/scrubber.py`.
  Only fires on the two real free-text intake paths: voice transcription (`intake/voice_path.py`)
  and image extraction (`intake/vision_path.py`) — both reachable today only via the floating chat
  assistant's mic/image buttons. The agent chain itself never scrubs (its inputs are synthetic,
  already-clean data).
- **Local SLM offline fallback (Ollama).** `backend/api_client.py`'s `get_llm()`/`get_embeddings()`
  wrap every gateway call used above (Diagnose, Plan, Chat classifier, embeddings for RAG) with
  `.with_fallbacks()` to a local Ollama model if `genailab.tcs.in` is unreachable. Invisible under
  normal conditions — no dedicated UI, it's a resilience net.
- **Chat Assistant** (outside the core 8-step chain). `backend/main.py`'s `POST /chat`. One LLM call
  (`gpt-4.1-nano`) classifies the user's message into an intent + structured filters; everything
  after that is deterministic — `query_tickets` runs a real parameterized SQL query (the model
  never invents a number), `approve_incident`/`reject_incident` reuses the exact same audited path
  Incident Workspace's own approval section uses.

## Part 2 — Overview tab, every metric

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
| **Manual triage avoided** ("alerts collapsed" gauge) | `metrics.correlation_noise_reduction_ratio` | `round(1 - n_clusters/len(alerts), 3)` — runs DBSCAN correlation (Part 1) over **every** alert in `data/alerts.json` (the full synthetic dataset, not just this session's), counts distinct `cluster_id`s. E.g. 200 alerts → 196 clusters = ~2% collapsed. This is the metric's only live consumer today (see Part 1's Correlate nuance). |
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

## Quick reference — LLM vs SLM vs classical ML vs deterministic, by step
| Step | Uses |
|---|---|
| Correlate | Classical ML (scikit-learn DBSCAN) |
| Enrich | Deterministic + RAG/vector search (Chroma, gateway embeddings) |
| Diagnose | LLM (DeepSeek R1, via A2A) |
| Plan | RAG (Chroma) + LLM (gpt-4.1-nano) + deterministic guardrails |
| Policy Gate | Deterministic rule engine |
| Execute | Deterministic (audit log only) |
| Verify | Deterministic (Fake Fix Detector) |
| Sync | Deterministic |
| Knowledge | Deterministic |
| Voice/image intake scrub | Local SLM (Ollama) + regex |
| Any gateway call, if gateway is down | Local SLM offline fallback (Ollama) |
| Chat assistant intent classification | LLM (gpt-4.1-nano) |
