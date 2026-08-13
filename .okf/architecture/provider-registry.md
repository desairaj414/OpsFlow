---
type: Module
title: LLM Provider Registry
description: backend/providers.py — the multi-provider LLM registry (Gemini default, OpenRouter/OpenAI/Grok/Custom as Bring Your Own Key options, TCS legacy/gated) with a per-role model map and a BYOK model-picker/validation API, replacing the original single-hardcoded-endpoint design.
resource: backend/providers.py
tags: [llm, config, providers]
status: stable
generated: { by: "claude-sonnet-5/okf-maintain", at: "2026-08-13T00:00:00Z" }
sources:
  - id: providers-py
    resource: backend/providers.py
    title: backend/providers.py
    last_modified: 2026-08-13
---

# Overview

`PROVIDERS: dict[str, dict]` holds one entry per LLM provider OpsFlow can talk to. Unlike a
single-`default_model`-per-provider design, each entry carries a `roles` map — `default`,
`reasoning`, `structured`, `vision` — because OpsFlow's agent chain calls distinct models for
distinct capability needs (see [Model Routing](model-routing.md)), not one general-purpose model
everywhere. `openai`/`grok`/`custom` (added for Bring Your Own Key — see below) carry an empty
`roles` map instead, since a visitor picking one of these always supplies an explicit model at
login; there's no curated default to fall back to.[^providers-py]

# Schema

| Provider id | Label | Base URL | Vision | Transcription | SSL bypass | `model_source` |
|---|---|---|---|---|---|---|
| `gemini` | Google Gemini | `generativelanguage.googleapis.com/v1beta/openai/` | yes | no | no | `static` |
| `openrouter` | OpenRouter | `openrouter.ai/api/v1` | yes | no | no | `fetch` |
| `openai` | OpenAI | `api.openai.com/v1` | yes | yes (`whisper-1`) | no | `fetch` |
| `grok` | xAI Grok | `api.x.ai/v1` | yes | no | no | `fetch` |
| `tcs` | TCS GenAI Lab (legacy, internal network only) | `config.BASE_URL` | yes | yes (Whisper) | yes | `manual` |
| `custom` | Custom (OpenAI-compatible) | visitor-supplied at login | yes | no | no | `fetch` |

Each entry also carries: `embedding_model` (or `None` — several providers have no embeddings
endpoint, and embeddings never actually read this per-provider value at request time regardless,
see [Embeddings Fixed Provider](/decisions/embeddings-fixed-provider.md)), `key_hint` (shown in the
Bring Your Own Key UI), and for `tcs` a `note` warning it's gated and unreachable from the public
deploy.

`model_source` drives the BYOK model picker in `LoginModeSelector.jsx`:
- `static` — a hand-curated, pre-verified list (`model_choices`, each `{id, label, tier}`). Only
  `gemini` uses this — its own `/models` listing wasn't trustworthy enough to build a picker from.
- `fetch` — the frontend calls `POST /providers/fetch-models` with the visitor's key (and, for
  `custom`, their base URL); on a non-empty result it shows a dropdown of returned model ids, on
  failure/empty it falls back to a manual text field.
- `manual` — no listing exists to fetch (`tcs`); always a manual text field.

# Roles

- `default` — general/summarization/self-check.
- `reasoning` — root-cause hypothesis generation (Diagnosis); needs genuine multi-step reasoning,
  tolerates higher latency.
- `structured` — remediation-plan drafting / chat filter-extraction; must return valid JSON
  reliably at a normal token budget (reasoning-heavy free models can burn the budget on hidden
  thinking tokens and truncate structured output — this shaped the actual model picks per role).
- `vision` — screenshot/error-image extraction.

`gemini`'s roles all point at `gemini-flash-lite-latest` — not one model per role. Live-testing
found `gemini-flash-latest` (originally used for reasoning/vision) has two disqualifying problems
for a public free-tier demo: it burns a capped `max_tokens` budget on invisible thinking tokens
(truncated/unparseable JSON), and its free tier caps at a hard 20 requests/day — too low for Free
Demo Key mode, meant to always work for public visitors. `-lite-latest` has neither problem at the
same prompts, trading reasoning depth for reliability. `openrouter`'s roles are `:free`-suffixed
model ids, live-verified against a real `OPENROUTER_API_KEY` (each tested with the actual prompt
shape its role sends) — the original guessed ids didn't exist in OpenRouter's free catalog at all
(see [Model Routing](model-routing.md)).

# Fixed module-level constants

- `DEMO_PROVIDER = "gemini"` — backs Free Demo Key mode (see [Demo Modes](/demo-modes/)); its key
  comes from `config.GEMINI_API_KEY`, a platform secret, never committed.
- `EMBEDDING_PROVIDER = DEMO_PROVIDER` — the provider used to embed/query Chroma, **regardless** of
  which provider a visitor's own session is on. See
  [Embeddings Fixed Provider](/decisions/embeddings-fixed-provider.md) for why.
- `DEFAULT_PROVIDER` — `os.getenv("DEFAULT_PROVIDER", DEMO_PROVIDER)`, used whenever a request
  doesn't specify a provider (local dev, tests, scripts).

# Functions

- `resolve_provider(name) -> str` — validates a provider name from a request header, falling back
  to `DEFAULT_PROVIDER` for anything missing or unrecognized.
- `api_key_for(provider, byok_key) -> str` — a visitor-supplied Bring Your Own Key wins if present;
  otherwise resolves the platform-configured key for that provider (`GEMINI_API_KEY`,
  `OPENROUTER_API_KEY`, or `config.API_KEY` for `tcs`).
- `resolve_base_url(provider, override_base_url) -> str` — every curated provider ignores a
  header-supplied base URL and keeps its own fixed one; only `custom` (whose registry entry has no
  base URL of its own) actually uses the override. Raises `ValueError` if `custom` has none.
- `resolve_model(provider, role, override_model) -> str` — a BYOK visitor's explicit model choice
  (set via the login-screen fetch/validate step, propagated as `X-LLM-Model`) wins over the curated
  per-role default for **any** provider, not just the three without one — so a visitor can, say,
  pick Gemini's Pro tier instead of the platform's Flash-Lite default. Free Demo Key and Instant
  Demo sessions never send this header, so they keep using the curated map unchanged. Raises
  `ValueError` if neither an override nor a curated default exists for that role (only possible for
  `openai`/`grok`/`custom` without a BYOK model choice — shouldn't happen given the frontend always
  collects one before login succeeds).
- `fetch_models(provider, api_key, base_url=None) -> list[str] | None` — best-effort
  `GET {base_url}/models`; returns a sorted id list, or `None` on any error/empty result (the
  frontend falls back to a manual model-id field). Backs `POST /providers/fetch-models`.
- `validate_key(provider, api_key, model, base_url=None) -> (bool, str | None)` — a minimal
  one-token `/chat/completions` call so a bad BYOK key/model is caught at login, not on the first
  real workflow run. Backs `POST /providers/validate-key`. Both functions mirror EduCare's
  `providers.py` helpers of the same name, adapted to read `needs_ssl_bypass` from this registry.
- `probe_transcription_support(provider, api_key, base_url=None) -> bool | None` — for every
  curated provider, `supports_transcription` is a verified, static fact about that provider's API
  surface (not something that varies by key or account credits — Gemini's OpenAI-compat layer has
  never exposed `/audio/transcriptions`, free tier or paid), so this returns the registry value
  directly, no network call. For `custom`, where the endpoint shape is genuinely unknown ahead of
  time, it POSTs a throwaway multipart payload to `{base_url}/audio/transcriptions` and classifies
  by status code alone: `404` means the route doesn't exist (no transcription); anything else means
  some handler answered at that path, so it's supported even though the garbage payload itself was
  rejected. Live-verified 2026-08-13 against a real endpoint known to lack this route (Gemini's own
  base URL, used as a stand-in `custom` endpoint) — correctly returned `False`. Deliberately **not**
  extended to vision: unlike transcription, vision has no dedicated URL of its own (it rides the
  same `/chat/completions` path as text), so a rejected test image can't be told apart from "this
  model can't see" — building that probe would produce an unreliable signal dressed up as a real
  one, so `custom`'s `vision: true` stays a documented assumption instead
  (`frontend/src/lib/providers.js`'s `visionUnverified` flag, shown to the visitor as a caveat
  rather than pretended-verified).

# BYOK model-picker + validation endpoints (`main.py`)

`POST /providers/fetch-models` and `POST /providers/validate-key` are deliberately unauthenticated
(no `Depends(get_current_identity)`) — they run from the login screen, before a visitor has any
token. Neither ever logs the API key in the request body. `LoginModeSelector.jsx` calls
`fetch-models` when its "Fetch available models" button is pressed (for `model_source: "fetch"`
providers), and calls `validate-key` both from its own "Validate & Save Key" button and, as a
safety net, from `page.js`'s `handleLogin` if the visitor never pressed that button — the login
form will not navigate to the cockpit on a missing or bad BYOK key/model; it shows the provider's
real error message inline instead (`frontend/src/lib/providers.js`'s `fetchByokModels()` /
`validateByokKey()`). On success, `validate-key`'s response also includes
`capabilities.supports_transcription` (via `probe_transcription_support()` above) — stored in
`providerMode.js`'s persisted mode and preferred by `providers.js`'s `canUseVoice()` over the
static `PROVIDER_INFO` default whenever it's present, which is what lets the mic button reflect a
`custom` endpoint's real, checked behavior instead of a blanket guess.

# Consumers

[Provider Propagation](provider-propagation.md) (the per-request active-provider mechanism and
`api_client.py`'s `get_llm()`/`get_embeddings()`), the voice and vision intake paths (see
[Intake](/intake/)), `scripts/pregenerate_demo_outputs.py` (see
[Pregenerate Script](/demo-modes/pregenerate-script.md)), and
[Public Hosting Modes](/demo-modes/public-hosting-modes.md)'s login-screen BYOK flow.

[^providers-py]: backend/providers.py
