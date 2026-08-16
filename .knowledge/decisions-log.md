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

- **Decision:** Re-theme the entire simulated domain (all 200 CIs, alerts, runbooks) from generic
  IT infrastructure (web-server/db-server/load-balancer/...) to Microsoft 365 & Power Platform
  business services (SharePoint, OneDrive, Power Platform, Teams, Exchange Online, Dataverse, Azure
  AD) — done as a mechanical relabelling of `data_gen`'s fixed-length seeded pools, not a data
  regeneration, so every CI's environment/criticality/blast-radius/relationships and every alert's
  ci_id/category/severity mapping stayed identical to pre-pivot (verified by spot-check + the full
  84/84 backend suite). Alongside this: per-tab plain-language explainer copy and a Microsoft-
  admin-center-styled visual redesign (navy header, azure accent tokens, underline tab nav).
- **Alternatives considered:** re-theme only the hero/demo-path CIs and leave the ~190 background
  CIs generic; a neutral (non-Microsoft-branded) enterprise SaaS visual style instead of the
  admin-center direction.
- **Rationale:** Human's explicit call, made off the original phase plan (between Phase 4 close and
  Phase 5 start) — the generic IT-infra framing and undocumented tab purposes read as too technical
  for a jury audience. Full-domain re-theme chosen over hero-only so a juror clicking anywhere in
  Ops Board/Drift Queue/etc. sees the same theme, not just the scripted golden path. See
  `state-progress.md` LAST VERIFIED STEP for the full implementation record.
- **Date:** 2026-08-07

- **Decision:** SUPERSEDES the PRD §4.3 "No real authentication" call above (originally: "zero
  marginal credit, real cost... Role switcher is simulated identity"). Implement real
  authentication: a `users` table (replaces `profiles`) with per-account salted PBKDF2-HMAC-SHA256
  password hashes (stdlib `hashlib`, no new dependency), `POST /auth/login` actually validates
  username+password and rejects bad credentials with 401, and each account has one fixed role (no
  more self-service role-picking at login or in the Sidebar). Admin retains a scoped, audited
  "View as" impersonation control (admin-only) for demo/testing, rather than the old free-for-all
  profile switcher any logged-in user could use to grant themselves Approver/Admin.
- **Alternatives considered:** keep the original mock/simulated-identity design and only fix the
  login page's copy to explain the separate role-picker step; a full third-party auth provider
  (OAuth/SSO) — rejected as disproportionate scope for a hackathon prototype with no real user base.
- **Rationale:** Human explicitly requested real authentication for "the fully fledged app" after
  the mock-login + free role-switcher combination read as confusing and, on reflection, insecure
  (any authenticated session could self-elevate to Admin). PBKDF2 via stdlib chosen over
  bcrypt/passlib specifically to avoid a new pip dependency in an environment where package
  installs have repeatedly hit corporate-proxy SSL friction (see `env-network.md`).
- **Date:** 2026-08-07

- **Decision:** SUPERSEDES the Microsoft-admin-center visual direction chosen just above. Full
  rebrand off Microsoft entirely (no logo, no product name, no "Microsoft 365" wording in chrome —
  the human judged even the admin-center-styled version too close to implying a Microsoft product)
  to a new original identity: **product name "Verascope"** ("vera" + "scope" — an instrument for
  seeing a true signal through noise, which is literally what correlation+diagnosis+verification
  do), a new logo (scope-ring mark: two concentric rings + center dot, teal→blue gradient SVG, no
  external asset), and a light-by-default, card-based token system (`--signal` teal `#0D9488` as
  the one brand hue, reused for the logo, primary actions, and the "system-verified" badge). New
  **Overview dashboard** (KPI tiles + bar/gauge/donut charts, all backed by existing real endpoints
  — `/metrics/summary`, `/cmdb/drift`, `/autonomy-ladder`, `/audit-log`) replaces Ops Board as the
  default landing tab for every role. Sidebar admin panels now open in a modal (dependency-free,
  built in-repo) instead of expanding inline in the 256px sidebar. A light/dark theme toggle was
  added afterward (Sidebar, both collapsed/expanded) — light is the true default (no
  `prefers-color-scheme` auto-detection; explicit `data-theme` + localStorage only), dark kept
  as the original token values, unchanged.
- **Alternatives considered:** keep the Microsoft-admin-center-styled theme from the prior decision
  and only swap the literal 4-square logo glyph for a generic one; auto-detect dark mode from OS
  preference (rejected per this session's explicit ask — light must be the default regardless of
  system setting, dark opt-in only).
- **Rationale:** Human's explicit call: "we can't use that Microsoft branding as our app name," plus
  a supplied reference dashboard image setting the structural direction (light, card-based, colorful
  KPI icon chips, grouped sidebar, gauge/donut charts) and an explicit request to use the
  `frontend-design` skill for the identity work and the `dataviz` skill for the new charts. The
  `dataviz` skill's colorblind-safety validator caught a real issue during this pass — red/green
  (the obvious first choice for an approvals-vs-rejections chart) fails the deutan separation check,
  so charts use a consistent teal/amber pairing instead.
- **Date:** 2026-08-07

- **Decision:** Human-directed pass (before Phase 5 resumes): make Ops Board readable to a
  first-time user, wire alerts to a local ITSM/Jira-shaped ticket lifecycle with click-to-diagnose,
  merge Runbook + Knowledge Base into one tab, fold Metrics & Eval into Overview. Staged as 4 steps,
  each human-verified before the next. Step 1 (readability) done — see state-progress.md. Key calls
  locked in for steps 2-4: (a) **click-to-diagnose per alert/cluster + one bounded "Run all
  untriaged" button**, not full auto-trigger on every SSE alert — avoids uncontrolled LLM spend and a
  concurrent-run architecture change; (b) **ticket + trace snapshot persisted to a new local
  `local_tickets` SQLite table**, additive only — does not touch the frozen `supervisor.py`/
  `sync.py`/`itsm_mcp.py` contracts that already create/update a real ServiceNow-shaped ticket per
  run; (c) new dummy Knowledge Base articles (Teams/SharePoint/Power Automate/Power Apps/Azure AD)
  chunked into the existing `"runbooks"` Chroma collection tagged `doc_type`, not a second collection;
  (d) `MetricsEval.jsx` deleted once its remaining stats (stopped-before-completion, negative-KB-
  seeded, scenario-eval-status) are folded into `Overview.jsx`.
- **Alternatives considered:** full auto-trigger on every incoming alert (rejected — uncontrolled
  concurrent LLM spend); a full normalized incident-history schema using the still-empty
  `evidence`/`hypotheses`/`plans` tables (rejected for this pass — a JSON trace-snapshot column is
  the lower-scope option that still satisfies "show me how a past alert was solved"); reworking the
  tested `itsm.py`/`tracker.py` simulators to persist directly (rejected — additive new table is
  lower-risk than touching frozen/tested code).
- **Rationale:** Human's explicit call after reviewing Ops Board's raw-payload-first display and
  asking "who looks at the app for the first time" — confirmed via AskUserQuestion on trigger model,
  history depth, and sequencing before any code was written (plan file, human-approved).
- **Date:** 2026-08-07

- **Decision:** Implemented the offline Ollama fallback for chat models that models-routing.md had
  already specified (PRD §3.2: "Offline fallback for demo resilience... must still run if the
  gateway dies mid-demo") but that had never actually been wired into code — `api_client.get_llm()`
  now transparently falls back to local `llama-3.2-3b-it` via LangChain's `.with_fallbacks()` on any
  enterprise-gateway failure. Deliberately did NOT wire an embeddings fallback into the live
  retrieval path (`orchestrator/retrieval.py`'s `_embed()`) — tested and confirmed it would raise
  Chroma's `InvalidDimensionException` on every query (existing collections are indexed at the
  enterprise model's 3072 dims; Ollama's `gte-large` is 1024), a worse failure than no fallback.
- **Alternatives considered:** `deepseek-r1` as the fallback chat model (semantically closer to the
  primary DeepSeek R1) — rejected after testing: 60s+ for a trivial reply and its `<think>` preamble
  breaks the agents' JSON parsing. `qwen-2.5.1-coder-it` — rejected, timed out at 60s with no
  response. A same-collection embeddings fallback — rejected after confirming the dimension-mismatch
  crash directly.
- **Rationale:** Human hit "Failed to fetch" on Ops Board's "Diagnose" button during a total TCS
  gateway outage and asked "can we use a model that works" — this was already the documented,
  PRD-mandated design, just never implemented; closing the gap, not a new decision. Chose
  `llama-3.2-3b-it` over the semantically-closer `deepseek-r1` on the same evidence-based standard
  the project has used for every prior model substitution (test candidates against a realistic
  prompt for THIS role, not just reachability).
- **Date:** 2026-08-07

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
