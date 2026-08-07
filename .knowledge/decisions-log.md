---
type: decision
title: Decisions Log
status: active
updated: 2026-08-07
related: [extra-credit.md, arch-overview.md, models-routing.md]
---

Pulled directly from `PRD_FINAL.md` §3.7, §4.0 and §4.3 (already-resolved decisions). One line
each: decision — alternative rejected — reason. **Do not re-litigate any of these.** If a phase
turns up a reason one should change, stop and tell the human; do not edit this log unilaterally.

## Log (from PRD §3.7 — alternatives considered)
- **Two-level Supervisor + specialists** — rejected: single do-everything agent, fully autonomous remediation, LLM-based correlation, off-the-shelf frameworks (LangGraph/CrewAI/AutoGen), routing all traffic over A2A, an MCP server that "coordinates agents". Reason: MAST data attributes 44.2%/32.3% of multi-agent failures to system design/misalignment; centralised validation bottleneck contains error amplification to ~4.4× vs ~17× uncoordinated.
- **Deterministic correlation (classical ML, CPU)**, not LLM-based — rejected: LLM event correlation. Reason: non-deterministic, expensive, unexplainable, worse than clustering at the task.
- **Closed-vocabulary deterministic voice intent parsing**, not LLM parsing or free-form dictation — rejected: LLM-based intent parsing, free-form voice dictation. Reason: a misheard command reaching an approval action is unacceptable; command-scope + on-screen confirmation is the safety choice.
- **MCP + A2A over an agent framework** — rejected: LangGraph/CrewAI/AutoGen. Reason: handbook rewards framework independence/explainability; MCP+A2A already provide the needed interop.
- **One A2A handoff only**, not routing all agent traffic over A2A — reason: the architectural claim needs exactly one demonstrated handoff; more is real implementation burden for no marginal credit.
- **Simulated ITSM/Tracker/Monitoring/CMDB (our own FastAPI)**, not real ServiceNow PDI — rejected: real ServiceNow PDI. Reason: hibernates ~24h, releases after 10 days, possible waitlist, licence framing, lab-network risk; simulators can also produce scenarios (50-alert storm, 6-month CMDB drift, planted credential) a real instance cannot produce on demand.
- **SQLite + Chroma**, not Postgres/Neo4j — reason: moderate data volume (hundreds of records); SQLite + an adjacency table covers CI relationships without overkill.
- **Structural chunking (heading/step boundaries)**, not fixed-size chunking — reason: naive fixed-size splitting can cut a runbook step mid-instruction, which is dangerous when the retrieved text is an action against production. See §6.4 / [domain-guardrails.md](domain-guardrails.md).

## Log (from PRD §4.0 — trade ledger, what was cut to fund voice/vision/full-parity tuning)
- **Cut scoped chat drawer** — reason: voice is now the conversational modality (D1), so the hybrid-interaction guidance is still satisfied without the "is this just a chatbot" framing risk.
- **A2A: three handoffs reduced to one** — reason: one handoff already proves the architectural claim.
- **Autonomy Ladder → status panel, not a live promotion engine** — reason: displaying the ladder makes the point; live promotion is a mid-term roadmap item (§2.7).
- **Maintenance Planner → a panel inside Incident Workspace, not its own screen** — reason: it was serving only one scenario.
- **Simulator field fidelity thinned to ~12 demo-relevant fields per system** — reason: authentic field *names* matter to jurors (`sys_id`, `fields.status.name`); full vendor data-model coverage does not.

## Log (from PRD §4.3 — explicitly not built)
- **No multilingual intake** — reason: the problem is machine-to-machine (alerts/CIs/logs/runbooks are English); inclusion effort was invested in accessibility (voice) instead.
- **No real ServiceNow PDI** — see rejection above.
- **No real script execution against live infrastructure** — reason: simulated execution with genuine state/metric movement is the honest, reproducible choice; never imply it is real infrastructure.
- **No ReAct-style open loops** — reason: "more turns made it worse" finding (ITBench); hard turn caps instead.
- **No real authentication** — reason: zero marginal credit, real cost. Role switcher is simulated identity, server-side enforced, stated as such.

## Template for any NEW decision made during execution
- **Decision:**
- **Alternatives considered:**
- **Rationale:**
- **Date:**
<!-- Append new decisions below this line, newest last -->

- **Decision:** Frontend stays/moves to Next.js, per the frozen PRD — the existing Vite/React
  scaffold will be migrated, not kept as a permanent deviation.
- **Alternatives considered:** Keep Vite/React (repo already has a working skeleton) and note the
  deviation in the README instead of migrating.
- **Rationale:** Human call, made explicitly to resolve the stack-mismatch flagged in
  `state-progress.md` KNOWN ISSUES — PRD_FINAL.md is frozen and specifies Next.js. Migration work
  itself is deferred to Phase 4 (Cockpit UI) since Phase 0-1 are backend-only; not done as
  emergency surgery on the working Vite skeleton mid-Phase-0.
- **Date:** 2026-08-07

- **Decision:** Vision-intake role (screenshot/error-image extraction) moves from the deprecated
  Llama Vision deployment to **`genailab-maas-gpt-4o`**.
- **Alternatives considered:** `gpt-4o-mini` (PASS, 1839ms, correct), `gpt-4.1` (PASS, 2296ms,
  correct), `gemini-2.5-flash` (PASS, 1596ms, correct), `sonnet-4.6` (PASS, 2808ms, correct),
  `gpt-4.1-mini` (PASS but answered "Pink" for a red test image — ruled out on accuracy).
- **Rationale:** Human explicitly delegated "pick the best substitute and use it" after
  double-confirming Llama Vision is permanently gone (404 then 410 on recheck, not transient).
  `gpt-4o` was fastest among the correct answers (975ms) and is already `DEFAULT_CHAT_MODEL` in
  `.env`, so no new model enters the routing table. Re-verified after wiring in: `smoke_test.py`'s
  dedicated vision check now PASSes end-to-end via this model.
- **Date:** 2026-08-07

- **Decision:** Extend `SpecialistResult` (frozen, 84/84-tested contract) with `latency_ms`/
  `tokens_used`/`transport` for the Agent Trace Viewer, rather than shipping the viewer without
  those fields or building a parallel data structure.
- **Alternatives considered:** ship the viewer with only what already existed (`model_used`,
  `evidence_ids`, `termination_reason`) and label latency/tokens/transport as not yet captured;
  pause the Trace Viewer step entirely and do a lower-risk step first.
- **Rationale:** Human chose to extend after being told this touches a contract the demo-complete
  gate had already verified — done additively (all new fields optional/defaulted) specifically so
  no existing construction call or test could break; reran the affected test suite (14/14) to confirm.
- **Date:** 2026-08-07

- **Decision:** `run_workflow` has no checkpointing (single straight-through async call, no
  persisted intermediate state) — an approval in the Approval Queue **re-runs the same CI fresh**
  with `auto_approve=true` rather than resuming the exact paused run. This is labeled honestly in
  the UI (new incident_id, not a continuation) rather than presented as a true resume.
- **Alternatives considered:** build real checkpointing (persist evidence/diagnosis/plan, resume
  from the pause point — more faithful to the PRD, but a real `supervisor.py` refactor); record the
  approve/reject decision only, without triggering any execution at all.
- **Rationale:** Human picked the re-run approach as the simplest honest option that still lets the
  approved plan actually execute end-to-end, given the scope/time tradeoff of building real
  workflow-resume machinery this late in the session.
- **Date:** 2026-08-07

- **Decision:** Build all of Phase 4's remaining hard-acceptance-criteria gaps (golden-path
  continuity, three-badge system, modality field, real voice approval, real image→IMG-nnn citation)
  rather than deferring the two bigger ones (voice/image intake wiring).
- **Alternatives considered:** close only the small/contained gaps (modality field, badge system)
  and explicitly defer golden path + voice + image as MOCK-P1/known limitations; stop at the
  8-tabs-built point and call it demo-ready without closing acceptance criteria at all.
- **Rationale:** Human explicitly chose full closure over deferring the bigger items, despite the
  larger scope (wiring `backend/intake/{voice_path,vision_path}.py` to real HTTP endpoints for the
  first time). Executed with the same verify-before-trust discipline as earlier steps — live curl
  tests before frontend wiring, 8/8 existing intake tests rerun after the one additive backend
  change (`intake_adapter.py` returning `incident_id`).
- **Date:** 2026-08-07

- **Decision:** Remediation/tuning-plan-drafting role moves from the deprecated DeepSeek V3
  deployment to **`azure/genailab-maas-gpt-4.1-nano`**.
- **Alternatives considered:** `gpt-4o-mini` (valid JSON, 3917ms, 461 tokens — already used
  elsewhere for summarisation/ticket-drafting/self-check), `gpt-4.1-mini` (valid JSON, 4002ms, 380
  tokens), `gemini-2.5-flash-lite` / `gemini-2.5-flash` (both returned truncated/invalid JSON — most
  of their token budget went to hidden reasoning tokens, unreliable for structured output at a
  normal budget), `Haiku-4.5` (valid JSON, 3499ms, 551 tokens).
- **Rationale:** Human explicitly delegated "do the same thing for it" after DeepSeek V3's
  deprecation was re-confirmed (410, not transient). Tested against a realistic structured-JSON
  remediation-plan prompt, not a trivial ping, since this role's whole job is producing valid
  structured output from runbook text. `gpt-4.1-nano` was fastest (1814ms) with valid JSON, and its
  cost tier best matches V3's original "cheaper than R1" positioning — kept it distinct from
  `gpt-4o-mini` (already used for 3 other roles) rather than consolidating further. Wired into
  `backend/.env` `HANDBOOK_MODELS`, re-verified end-to-end via `smoke_test.py`.
- **Date:** 2026-08-07
