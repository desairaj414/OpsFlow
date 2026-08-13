---
type: Module
title: Provider Propagation
description: How a visitor's chosen LLM provider/mode (Instant Demo / Bring Your Own Key / Free Demo Key) reaches every LLM call site without threading a parameter through the whole Supervisor -> specialist chain.
resource: backend/provider_context.py
tags: [llm, architecture, request-scoped]
status: stable
generated: { by: "claude-sonnet-5/okf-maintain", at: "2026-08-13T00:00:00Z" }
sources:
  - id: provider-context-py
    resource: backend/provider_context.py
    title: backend/provider_context.py
    last_modified: 2026-08-13
  - id: api-client-py
    resource: backend/api_client.py
    title: backend/api_client.py
    last_modified: 2026-08-13
---

# Overview

A visitor's testing mode is picked once, on the frontend, and persisted in `localStorage` (see
`frontend/src/lib/providerMode.js`). Every request goes through `apiFetch()`
(`frontend/src/lib/api.js`), which attaches it as plain HTTP headers: `X-LLM-Provider` (a provider
id, or the literal string `instant_demo`), and, for Bring Your Own Key, `X-LLM-Api-Key` plus (once
the visitor has picked or fetched a model at login) `X-LLM-Model` and, for the `custom` provider
only, `X-LLM-Base-Url`.[^provider-context-py]

On the backend, the FastAPI dependency `get_provider_context()` reads those headers once per
request and sets four `contextvars` (`_active_provider`, `_active_api_key`, `_active_model`,
`_active_base_url`) for that request's duration. Anything downstream — `api_client.py`,
`intake/voice_path.py`, `intake/vision_path.py` — reads the same contextvars via
`get_active_provider()`/`get_active_api_key()`/`get_active_model()`/`get_active_base_url()`,
instead of the Supervisor threading an explicit parameter through every agent's frozen, tested
signature.[^provider-context-py] `_active_model`/`_active_base_url` stay `None` unless a BYOK
session set them — Free Demo Key and Instant Demo never send those two headers, so they keep using
each provider's curated per-role model map (`providers.resolve_model()` falls through to it). No
header sent at all (local dev, `smoke_test.py`, pytest) falls back to `providers.DEFAULT_PROVIDER`,
so none of those call sites had to change behavior for this refactor.

# Instant Demo short-circuit

If `X-LLM-Provider: instant_demo`, `get_provider_context()` returns
`ProviderContext(provider=INSTANT_DEMO, is_instant_demo=True)` without ever touching the LLM
contextvars meaningfully — callers check `provider_ctx.is_instant_demo` and branch to reading
pregenerated output instead of making any live call (see
[Instant Demo](/demo-modes/public-hosting-modes.md) and `main.py`'s `/workflows/run`, `/chat`).

# `api_client.py` — the client factory that reads this context

`get_llm(role, temperature, enable_offline_fallback)` builds a `ChatOpenAI` bound to whichever
provider is active on the current request, resolving the base URL and model via
`providers.resolve_base_url()`/`providers.resolve_model(provider, role, override)` (see
[Provider Registry](provider-registry.md)) rather than a literal model id — so the same call site
works unchanged across every provider, and a BYOK visitor's explicit model choice overrides the
curated default automatically. It wraps the primary client with LangChain's
`.with_fallbacks([...])` to a local Ollama model, independent of which provider is primary — this
resilience layer (originally built against the single TCS endpoint) still applies per-provider
after the multi-provider refactor.[^api-client-py] `intake/voice_path.py`'s `_transcribe()` and
`intake/vision_path.py`'s `_extract()` follow the same pattern for their own raw `httpx` calls —
voice always uses the provider's fixed `whisper_model` (transcription is a distinct capability from
the visitor's chosen chat/vision model override), while vision resolves its model the same way
`get_llm(role="vision", ...)` does.

`get_embeddings()` deliberately does **not** read this per-request context — see
[Embeddings Fixed Provider](/decisions/embeddings-fixed-provider.md).

# Security note

The BYOK key only ever lives in the `_active_api_key` contextvar for the lifetime of one request —
never written to `audit_log`, never logged, never persisted.[^provider-context-py]

# Consumers

[Diagnosis Agent](/agents/diagnosis-agent.md), [Planner Agent](/agents/planner-agent.md) (both call
`get_llm()` with a role), [Voice Intake](/intake/voice-intake.md), [Vision Intake](/intake/vision-intake.md),
and the chat assistant's intent classifier (`main.py`'s `POST /chat`).

[^provider-context-py]: backend/provider_context.py
[^api-client-py]: backend/api_client.py
