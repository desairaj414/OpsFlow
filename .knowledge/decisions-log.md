---
type: decision
title: Decisions Log
status: active
updated: 2026-08-17
related: [decisions-log-history.md, reference/future-plans.md, architecture/arch-overview.md, architecture/models-routing.md]
---

Pulled directly from `PRD_INITIAL.md` §3.7, §4.0 and §4.3 (already-resolved decisions; file moved
+ renamed from root `PRD_FINAL.md` 2026-08-17). One line each: decision — alternative rejected —
reason. **Do not re-litigate any of these.** If new work turns up a reason one should change, stop
and tell the human; do not edit this log unilaterally.

## Log (from PRD §3.7 — alternatives considered)
- **Two-level Supervisor + specialists** — rejected: single do-everything agent, fully autonomous remediation, LLM-based correlation, off-the-shelf frameworks (LangGraph/CrewAI/AutoGen), routing all traffic over A2A, an MCP server that "coordinates agents". Reason: MAST data attributes 44.2%/32.3% of multi-agent failures to system design/misalignment; centralised validation bottleneck contains error amplification to ~4.4× vs ~17× uncoordinated.
- **Deterministic correlation (classical ML, CPU)**, not LLM-based — rejected: LLM event correlation. Reason: non-deterministic, expensive, unexplainable, worse than clustering at the task.
- **Closed-vocabulary deterministic voice intent parsing**, not LLM parsing or free-form dictation — rejected: LLM-based intent parsing, free-form voice dictation. Reason: a misheard command reaching an approval action is unacceptable; command-scope + on-screen confirmation is the safety choice.
- **MCP + A2A over an agent framework** — rejected: LangGraph/CrewAI/AutoGen. Reason: handbook rewards framework independence/explainability; MCP+A2A already provide the needed interop.
- **One A2A handoff only**, not routing all agent traffic over A2A — reason: the architectural claim needs exactly one demonstrated handoff; more is real implementation burden for no marginal credit.
- **Simulated ITSM/Tracker/Monitoring/CMDB (our own FastAPI)**, not real ServiceNow PDI — rejected: real ServiceNow PDI. Reason: hibernates ~24h, releases after 10 days, possible waitlist, licence framing, lab-network risk; simulators can also produce scenarios (50-alert storm, 6-month CMDB drift, planted credential) a real instance cannot produce on demand.
- **SQLite + Chroma**, not Postgres/Neo4j — reason: moderate data volume (hundreds of records); SQLite + an adjacency table covers CI relationships without overkill.
- **Structural chunking (heading/step boundaries)**, not fixed-size chunking — reason: naive fixed-size splitting can cut a runbook step mid-instruction, which is dangerous when the retrieved text is an action against production. See §6.4 / [domain-guardrails.md](domain/domain-guardrails.md).

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

**2026-08-07 (hackathon-day) decisions moved to
[decisions-log-history.md](decisions-log-history.md)** for space — Next.js migration, vision/DeepSeek-V3
model substitutions, `SpecialistResult` extension, no-checkpointing, Phase 4 full closure, M365
re-theme, real authentication, the original Verascope rebrand (see the newer superseding entry
below for its correction), the Ops Board readability pass, and the offline Ollama fallback. Do not
re-litigate any of them.

- **Decision:** Removed the demo-only "Start incident" CI-picker bar entirely (not kept as an
  admin/dev shortcut) now that real alerts drive diagnosis. New alerts arriving live now
  auto-trigger diagnosis, bounded to genuinely new arrivals (not the ~420 existing backlog, which
  stays a manual "Run all untriaged" action) — a notification bell in the header surfaces them.
- **Alternatives considered:** keeping the CI-picker bar as an admin-only "quick test" shortcut for
  demoing the 3 golden-path scenarios on demand — rejected, human's call. Auto-diagnosing the entire
  backlog too, with no manual step anywhere — rejected as uncontrolled LLM spend with no pacing.
- **Rationale:** Confirmed via AskUserQuestion — both the recommended options. This also surfaced a
  real bug (see the async-fix entry directly below): running diagnosis continuously in the background
  demonstrated how badly `llm.invoke()`'s event-loop blocking degrades the app, which a one-off
  manual click had never made obvious.
- **Date:** 2026-08-08

- **Decision:** REVERSES the §4.0 "cut scoped chat drawer" decision above — added a floating
  assistant (`ChatWidget.jsx`, `POST /chat`) and moved push-to-talk voice into its mic button,
  removing the Sidebar's standalone push-to-talk entirely.
- **Alternatives considered:** freeform LLM-generated SQL against `app.db` for the "ask about my
  tickets" capability (rejected — real injection/correctness risk, and the one part of this app
  that would let a model execute unconstrained code, breaking the pattern every other AI-touching
  component here follows); keeping push-to-talk in the Sidebar as a second, separate voice surface
  alongside the new chat mic (rejected, human's explicit call — one conversational surface, not two).
- **Rationale:** Human's explicit ask, for product-interactivity/enterprise-readiness reasons. The
  original decision's stated reason (PRD §2.2: a chat assistant is "a single-turn advisor with no
  hands and no memory of your estate... will confidently answer even with no evidence," which is
  why voice was chosen as the sole conversational modality instead) was surfaced back to the human
  before building, since reversing it undoes an explicit, argued PRD position — confirmed via
  AskUserQuestion, then built to preserve exactly the properties that argument relied on rather
  than becoming the thing it warned against: ticket/incident answers come from a real deterministic
  DB query (the LLM only extracts filters — same "LLM proposes, code executes" split as Diagnosis/
  Planner, never freeform SQL or fabricated numbers); approve/reject reuses the exact same audited,
  reason-required, role-gated `/workflows/decision` path Incident Workspace's own approval section
  uses, not a shortcut; app-help answers are grounded in a fixed description of this app only, told
  explicitly not to answer general IT/ServiceNow/Jira questions outside that scope. Voice input
  transcribes through the same real Whisper+scrubber pipeline as before (`/intake/voice`), then the
  transcript is handled as an ordinary chat message — one pipeline, not two parsers.
- **Date:** 2026-08-08

- **Decision:** POST-SUBMISSION (after the hackathon's own "Final Submission" commit). Pivoted the
  app from a single hardcoded TCS GenAI Lab endpoint (reachable only on the TCS corporate network)
  to a multi-provider LLM architecture (`backend/providers.py`: Gemini default, OpenRouter fallback,
  TCS retained as a gated legacy option, later expanded to 6 BYOK providers total), plus a 3-mode
  public demo UX (Instant Demo / Bring Your Own Key / Free Demo Key) so the app can run as a public,
  self-serve resume artifact instead of only on-site. Full detail lives in the OKF bundle, not
  duplicated here — see `.okf/decisions/multi-provider-architecture.md` and
  `.okf/architecture/provider-registry.md`.
- **Alternatives considered:** keep the single-endpoint design and document the public-hosting
  limitation in the README instead of building provider abstraction.
- **Rationale:** No reachable backend and no usable key exists for a visitor outside the TCS
  network under the original design. Gemini's free tier covers chat+vision with one key and is
  OpenAI-compatible, so existing `ChatOpenAI` plumbing needed parameterizing, not a rewrite.
  `models-routing.md`'s task→model-id table describes the pre-pivot state and should be read
  skeptically against current code; the routing *principle* it documents still holds.
- **Date:** 2026-08-11 (bundle-documented; exact code-change date not logged here at the time)

- **Decision:** Hosting is Render-only — a Python Web Service for the backend
  (`opsflowapp-backend`) and a static-exported Site for the frontend (`opsflowapp`, Next.js
  `output: "export"`) — not split across Render + Vercel, and not merged into one process. Full
  detail (alternatives, rationale, the Blueprint-vs-API-created-service distinction, the
  `opsflow-*` → `opsflowapp*` rename after a name collision) lives in
  `.okf/decisions/hosting-platform.md` — not duplicated here.
- **Alternatives considered:** Vercel (frontend) + Render (backend) — the original plan; one Render
  Web Service serving both (rejected, would put the always-warm-capable frontend under the
  backend's cold-start sleep for no benefit); fully serverless (rejected outright — SQLite/Chroma
  and the `/alerts/stream` SSE connection both need a long-running process).
- **Rationale:** Once the frontend's static-export viability was confirmed (one route, no
  `app/api/`, no middleware, no `next/image`), Render's free Static Site tier beat both a second
  platform and Render's paid Node Web Service tier ($7/mo minimum, confirmed live) — genuinely
  free, always-warm, CDN-backed, with zero UX tradeoff.
- **Date:** 2026-08-14 (hosting decision); service rename to `opsflowapp`/`opsflowapp-backend` 2026-08-15

- **Decision:** Retire phase-based execution tracking entirely. Every remaining item in
  `prd-phase-5.md` (Scenario Library, Eval & Hardening — the only phase not fully closed),
  `prd-phase-6.md` (Extra Credit), and `prd-phase-7-final.md` (Freeze & Packaging) was individually
  triaged against the app's actual current state (multi-provider, publicly hosted, post-submission)
  rather than mechanically executed as originally scoped. Outcome: `prd-phase-0.md` through
  `prd-phase-7-final.md` and `extra-credit.md` deleted; `CLAUDE.md`'s hub index and
  `state-progress.md` updated to drop phase-gated framing in favor of plain ongoing-state tracking.
  Per-item triage:
  - **Phase 5** — built out for real: 4 more scenario fixtures (10 total non-edge), 4 edge-case
    fixtures for the 4 edge types not already covered elsewhere, `backend/eval/harness.py` (new),
    `backend/orchestrator/cache.py` wiring the previously-unused `model_call_cache` table into
    diagnosis/planner, a low-quality/legacy-UI screenshot fixture. Two of the six originally-planned
    edge cases (scrubber catch, prompt-injection line) were found **already built and measured** in
    Phase 2/3 via `pii_ground_truth.json` + the scrubber's own test suite — not rebuilt as
    duplicate scenario fixtures. Real voice samples were left genuinely open (need a human to record
    them; PRD requires real speech, not synthetic) per the human's explicit choice when asked.
  - **Phase 6** — not built. Reframed entirely: it was scoped as "extra credit for judges" ahead of
    a hackathon deadline that has already passed (commit `6299a26`). Every original item was
    individually re-evaluated for whether it's still worth doing now that the app is a hosted public
    product, not a judged demo — see `future-plans.md` (new) for the full per-item verdict and scope.
  - **Phase 7** — effectively already done, in a better form, by post-submission work never
    attributed to it: `README.md` (actively maintained, far more current than the phase spec's
    README requirements) already covers the gateway/simulated-systems/MCP-A2A disclaimers this phase
    called for. The phase's other deliverables (deck outline, demo video, round-robin rehearsal) were
    hackathon-judging-specific with no ongoing audience. Its stale, never-updated-since-2026-08-08
    byproducts (`ARCHITECTURE.md`, `DEMO_SCRIPT.md`, `APP_FLOW.md`, `PROJECT_STRUCTURE.md`,
    `SETUP.md` — all pre-pivot, single-TCS-gateway/DeepSeek/Llama-Vision content) were deleted as
    redundant with `README.md`.
  - **New finding, not acted on:** `guardrails/policy_gate.py`'s `FREEZE_WINDOW`/
    `MAX_CONCURRENT_CHANGES` rules are fully built and unit-tested but never reachable from a live
    workflow run (`planner.py` always passes an empty `PolicyContext()`) — real, silent gap, scoped
    in `future-plans.md`, not fixed here since it wasn't what was asked.
- **Alternatives considered:** Mechanically complete every remaining Phase 5/6/7 checklist item as
  originally scoped, regardless of current relevance (rejected — the human explicitly asked not to
  duplicate/rebuild things that already exist in a better form elsewhere); leave the phase docs in
  place indefinitely as historical record without retiring the tracking model (rejected — the
  explicit goal was that a future session's resume shouldn't perceive incomplete phases as
  outstanding work).
- **Rationale:** Human's explicit request: check each phase's remaining scope against everything
  built since (the multi-provider pivot, hosting, mobile-responsive pass, and the many off-plan UI
  passes), build what's genuinely still worth it, don't duplicate what already exists in a different
  form, and clean up the phase-tracking apparatus itself once resolved so it stops implying
  unfinished phase work on every future session resume.
- **Date:** 2026-08-17

- **Decision:** SUPERSEDES the "full rebrand off Microsoft entirely... product name 'Verascope'"
  decision above. The app is, and remains, **OpsFlow** — that rebrand was reverted the same day it
  was introduced, before the hackathon's own Final Submission. Confirmed by git history, not
  assumption: `Logo.jsx` introduced "Verascope" branding in commit `f731300` ("Final Draft 1",
  2026-08-08 05:45), then was reverted back to "OpsFlow" in commit `6299a26` ("Final Submission",
  2026-08-08 10:14) — under 5 hours later, same day. The decision entry above was never corrected to
  reflect the reversal at the time (it describes the mid-draft state, not the shipped state), which
  left every later note built on top of it (this file, `state-progress-history.md`) describing
  "Verascope" as the live product identity when it never actually was one, past a same-day draft.
  All references corrected this pass: `frontend/src/lib/theme.js`'s `THEME_STORAGE_KEY` (was
  `"verascope-theme"`, a real shipped-but-harmless naming leftover — a returning visitor with the
  old key just gets the light-default theme once, same as a first-time visitor), `.okf/index.md`,
  `state-progress.md`, `state-progress-history.md`.
- **Alternatives considered:** Actually rebrand to Verascope now, to match what the decision log
  claimed (rejected — the human confirmed OpsFlow is correct and current; the log was wrong, not the
  code); leave the stale references in place with just a caveat note (rejected — the human explicitly
  asked for every reference corrected, not just flagged).
- **Rationale:** Human's explicit correction after last session's cleanup pass flagged the
  discrepancy as unresolved ("found, not fixed"). Investigated with `git log -S"Verascope"` rather
  than guessing — the full timeline was a same-day draft-and-revert inside the original hackathon
  session, not a mysterious later regression.
- **Date:** 2026-08-17

- **Decision:** Fixed `guardrails/policy_gate.py`'s dead `FREEZE_WINDOW`/`MAX_CONCURRENT_CHANGES`
  rules (`planner.py` always passed an empty `PolicyContext()`, so neither could ever fire) —
  **scoped to `patching` workflows only**, not universally. `active_changes_in_environment` is a
  live COUNT of `local_tickets` rows at `status_normalized='needs_approval'` per environment (that
  status is exclusively live-run-set, never present in bulk-seeded history). `freeze_windows` reuses
  the existing `patch_mcp.get_change_calendar()` call.
- **Alternatives considered:** Wire `freeze_windows` universally, to every workflow type — tried
  first, immediately broke 4 supervisor tests: `data/change_calendar.json`'s global blackout window
  (`BLACKOUT-G01`) is deliberately date-ranged to include "now" so the Patch Management demo always
  has a current blackout to show, and blocking incident remediation because of an unrelated code
  freeze isn't correct ITSM behavior (real practice exempts emergency/break-fix work from standard
  change freezes) — rejected once the regression showed why.
- **Rationale:** Human explicitly asked for the dead-code gap (found during the Phase 5 cleanup
  pass) to be fixed, not just documented in `future-plans.md`. `patching`-only scoping is the
  correct domain boundary (change-freeze windows are a change-management concept; `patching` is
  this project's own planned-change workflow type), not a workaround to make tests pass — confirmed
  by re-running the full suite (96/2 green) and the eval harness (14/14, twice) after the fix, with
  `SCEN-04`/`SCEN-08`'s `expected` blocks updated to include the now-real `blocked` outcome rather
  than treating it as a failure to hide.
- **Date:** 2026-08-17
