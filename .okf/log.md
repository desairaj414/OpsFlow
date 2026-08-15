# Update Log

## 2026-08-15
* **Maintain**: Live Render services renamed. The original Blueprint-created deploy
  (`opsflow-backend`/`opsflow-frontend`) had both names collide with another Render account,
  landing on random-suffixed URLs (`opsflow-backend-k6xm`, `opsflow-frontend-fz2u`). Recreated both
  directly via Render's API/MCP under `opsflowapp-backend`/`opsflowapp` — both landed with clean,
  suffix-free URLs. `render.yaml`'s `name:` fields updated to match, so a future Blueprint sync
  stays consistent with the live services; `README.md`'s live-demo link and §9 walkthrough updated
  to match. Old `opsflow-backend`/`opsflow-frontend` services left running pending manual deletion
  (no delete tool in this Render MCP server's toolset). Updated:
  [Hosting Platform](decisions/hosting-platform.md).

## 2026-08-14
* **Maintain**: `data/chroma_db/` (the built vector index) is now committed to git instead of
  gitignored, and `render.yaml`'s backend `buildCommand` no longer runs `db/load_chroma.py`.
  Real incident: Render's build ran `db/load_chroma.py` fresh on every deploy, re-embedding ~700
  chunks through Gemini's free-tier embeddings API, which is rate-limited tightly enough (429s,
  even with 5x retry/backoff) to fail the build outright. Since the source data is frozen synthetic
  seed content that never changes, the fix is to commit the already-built, self-test-passing index
  and only re-run `load_chroma.py` locally (then recommit) if that source data ever actually
  changes. Updated: [Database Schema](data/database-schema.md).
* **Maintain**: `api_client.py`'s `get_llm()` fallback chain gained a real intermediate step —
  OpenRouter, using the platform's own `OPENROUTER_API_KEY` — but scoped tightly: only for Free
  Demo Key sessions (no visitor-supplied key, active provider is `providers.DEMO_PROVIDER`), never
  for Bring Your Own Key (a visitor's own key/provider choice stays exclusive; rerouting their
  request through the deployer's key would spend the deployer's quota without consent). Prompted by
  a user question during Render deployment prep: the existing Ollama fallback is a no-op on a
  hosted deploy (no local Ollama process there), so before this change a Free Demo Key session had
  no *working* fallback at all if the shared Gemini key hit its quota — confirmed by inspecting the
  constructed `RunnableWithFallbacks` chain directly for three cases (Free Demo Key, BYOK+Gemini,
  BYOK+OpenRouter) rather than assuming. Updated: [Model Routing](architecture/model-routing.md).
* **Maintain**: Hosting plan changed from Vercel (frontend) + Render (backend) to Render-only —
  a Web Service for the backend plus a free Static Site for the frontend (Next.js
  `output: "export"`), one platform instead of two, verified free tier had no cost or UX
  regression (checked live: Render's free tier has no free Node web service, but does have a free,
  always-warm, CDN-backed Static Site tier; the frontend has zero server-side routes so static
  export is a clean fit — confirmed with an end-to-end Playwright pass against the exported build).
  New: [Hosting Platform](decisions/hosting-platform.md). Updated: `render.yaml` (added the
  `opsflow-frontend` static site service), `README.md` (new §9 "Deploying your own copy", live-demo
  link placeholder wording, BYOK provider list in §8's mode table).

## 2026-08-13
* **Maintain**: Evaluated static-registry vs. live-probe capability detection for voice/vision and
  implemented a hybrid: the 5 curated providers keep their static, hand-verified
  `supports_transcription`/`vision` flags unchanged (these are facts about each provider's API
  surface, not the visitor's account — probing them live would add latency/failure modes for zero
  accuracy gain). New `providers.py` `probe_transcription_support()` adds a real check only for
  `custom`, where the endpoint is genuinely unknown: POSTs a throwaway payload to
  `/audio/transcriptions` and classifies by 404-vs-not, live-verified against a real endpoint known
  to lack the route. `POST /providers/validate-key` now returns `capabilities.supports_transcription`;
  `providerMode.js`/`providers.js`'s `canUseVoice()` prefer it over the static default when present.
  Vision deliberately has no equivalent probe for `custom` — it shares `/chat/completions` with
  text, so a rejected test image can't be told apart from "unsupported"; instead the login UI now
  shows an explicit "assumed, not verified" caveat for it. Updated:
  [Provider Registry](architecture/provider-registry.md), [Voice Intake](intake/voice-intake.md).
* **Maintain**: `guardrails/scrubber.py`'s `ScrubResult.slm_pass_ran` (whether the local-Ollama
  free-text-name pass actually ran, vs. failed closed because no local Ollama was reachable — the
  normal case off the TCS network) used to dead-end in that dataclass, discarded by both intake
  paths. Now copied onto the canonical `MaintenanceSignal` contract (`orchestrator/contracts.py`,
  new optional field, both `run_voice_intake()`/`run_vision_intake()` set it) and surfaced as an
  inline warning in `ChatWidget.jsx` when `false`, so a missing local SLM degrades visibly instead
  of silently under-scrubbing free-text names. Also corrected two facts in
  [Voice Intake](intake/voice-intake.md) that had gone stale: transcription support now also
  includes `openai` (not just `tcs`), and the Sidebar's push-to-talk mic was already retired in
  favor of the Chat Widget's mic button — that consolidation had never been reflected here. Updated:
  [Scrubber](guardrails/scrubber.md), [Voice Intake](intake/voice-intake.md),
  [Vision Intake](intake/vision-intake.md). `.knowledge/api-contract.md` updated to match.
* **Maintain**: `providers.py` grew from 3 providers to 6 — added `openai`, `grok` (xAI), and
  `custom` (visitor-supplied OpenAI-compatible endpoint) as Bring Your Own Key options alongside
  the existing `gemini`/`openrouter`/`tcs`. New `model_source` field (`static`/`fetch`/`manual`)
  drives a login-screen model picker; new `resolve_model()`/`resolve_base_url()` let a BYOK
  visitor's explicit model/base-URL choice override the curated per-role default for *any*
  provider; new `fetch_models()`/`validate_key()` back two new unauthenticated endpoints
  (`POST /providers/fetch-models`, `POST /providers/validate-key`) so a bad BYOK key is caught at
  login, not on the first live workflow call. Two new request headers, `X-LLM-Model` and
  `X-LLM-Base-Url`, propagate alongside the existing `X-LLM-Provider`/`X-LLM-Api-Key`. Frontend:
  `LoginModeSelector.jsx` reworked (previously a cramped two-column key input that visually
  disappeared in the login card — now full-width stacked fields with a show/hide key toggle) and
  `page.js`'s login form now blocks navigation to the cockpit on a missing/invalid BYOK key,
  surfacing the provider's real error inline instead of silently proceeding. Updated:
  [Provider Registry](architecture/provider-registry.md), [Provider Propagation](architecture/provider-propagation.md),
  [Public Hosting Modes](demo-modes/public-hosting-modes.md) (also corrected two facts that had
  gone stale since 2026-08-11: Gemini's roles all consolidated onto `-lite-latest`, not split by
  role, and the mode-selector UI — previously logged as a "known gap" — has existed since before
  this date; that note was never removed).

## 2026-08-11
* **Creation**: Initial OKF v0.2 bundle, distilled from `.knowledge/*.md` (24 files), `PRD_FINAL.md`,
  and the current backend/frontend source (`backend/providers.py`, `provider_context.py`,
  `api_client.py`, `main.py`, `orchestrator/`, `agents/`, `guardrails/`, `intake/`, `a2a/`,
  `mcp_servers/`, `db/schema.sql`, `frontend/src/lib/`, `frontend/src/components/`). Captures the
  system **as it stands mid-refactor**: a multi-provider LLM architecture (Gemini default,
  OpenRouter fallback, TCS retained as a legacy/gated provider) replacing the original
  single-hardcoded-TCS-endpoint design, plus the three public-hosting demo modes being built on top
  of it (Instant Demo, Bring Your Own Key, Free Demo Key). [Getting Started](getting-started.md);
  [Architecture](architecture/) (tier diagram, provider registry, provider propagation, model
  routing, cockpit UI, Overview-tab metrics); [Agents](agents/) (Supervisor + 6 specialists + the
  one A2A handoff); [Tools](tools/) (MCP layer); [Guardrails](guardrails/) (policy gate, blast
  radius, scrubber, bias mitigation, chunking); [Intake](intake/) (voice, vision);
  [Workflows](workflows/) (incident/patch/performance parity); [Data](data/) (SQLite + Chroma
  schema); [Demo Modes](demo-modes/) (the 3 public-hosting modes + the pregenerate script);
  [Decisions](decisions/) (two-level Supervisor topology, one A2A handoff, the multi-provider
  pivot, the fixed embeddings provider, no-checkpointing re-run behavior, real authentication).
  Deliberately excluded: the hour-by-hour hackathon schedule, the day-by-day execution/verification
  log (`state-progress.md`, `state-progress-history.md`), and the phase-gate checklists
  (`prd-phase-*.md`) — these are hackathon-process artifacts, not portable system knowledge.
