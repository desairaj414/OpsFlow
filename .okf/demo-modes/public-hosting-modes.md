---
type: System
title: Public Hosting Modes
description: Three visitor-chosen ways to run OpsFlow — Instant Demo (zero live calls), Bring Your Own Key (visitor supplies a provider + key), and Free Demo Key (a Gemini key the operator controls) — replacing a design that only worked on the TCS corporate network.
tags: [demo, hosting, llm]
status: stable
generated: { by: "claude-sonnet-5/okf-maintain", at: "2026-08-13T00:00:00Z" }
sources:
  - id: provider-mode-js
    resource: frontend/src/lib/providerMode.js
    title: frontend/src/lib/providerMode.js
    last_modified: 2026-08-13
  - id: main-py
    resource: backend/main.py
    title: backend/main.py
    last_modified: 2026-08-13
  - id: login-mode-selector-jsx
    resource: frontend/src/components/LoginModeSelector.jsx
    title: frontend/src/components/LoginModeSelector.jsx
    last_modified: 2026-08-13
---

# Overview

`frontend/src/lib/providerMode.js` persists one of three modes in `localStorage`:
`{mode: "instant_demo" | "byok" | "free_demo", provider, byokKey, model, baseUrl, validated}`.
Default is `{mode: "free_demo", provider: "gemini", byokKey: null, model: null, baseUrl: null,
validated: true}`.[^provider-mode-js] `model`/`baseUrl` are only ever set for `byok` sessions (see
below); `validated` gates whether `page.js`'s login form will let the visitor into the cockpit.
Every request attaches the active mode as headers (see
[Provider Propagation](/architecture/provider-propagation.md)), which the backend resolves into a
`ProviderContext`.

`LoginModeSelector.jsx`, rendered below the credentials form on the login screen, is the mode-
selector UI — three mode cards, a Bring Your Own Key panel (provider dropdown across all six
[Provider Registry](/architecture/provider-registry.md) entries, API key field with a show/hide
toggle, a model field whose shape follows that provider's `model_source`, and a "Validate & Save
Key" button), and role quick-fill buttons (Ops Engineer / Approver / Admin) that autofill the
seeded demo credentials so a visitor can prove login works without hunting for them in the
README.[^login-mode-selector-jsx]

# Instant Demo — zero live calls

When `X-LLM-Provider: instant_demo`, endpoints that would otherwise call a model instead read from
a pregenerated `data/demo_outputs.json` (built by [Pregenerate Script](pregenerate-script.md)).
`POST /workflows/run` looks up `f"{ci_id}:{workflow_type}"` and 400s with an explanatory message if
the requested combination isn't one of the pregenerated scenarios — a visitor gets a real,
previously-verified result with genuinely zero live model spend, at the cost of only covering the
handful of named scenarios.[^main-py] `POST /chat` and the voice/image intake endpoints similarly
short-circuit to an explanatory message rather than attempting a live call.

# Bring Your Own Key — visitor supplies provider + key

The visitor picks a provider (any of the six in [Provider Registry](/architecture/provider-registry.md):
`openai`/`gemini`/`openrouter`/`grok`/`tcs`/`custom`), supplies their own API key, and picks (or
fetches) a specific model — all three sent as `X-LLM-Api-Key`/`X-LLM-Model`/(for `custom`)
`X-LLM-Base-Url`. `providers.api_key_for()` prefers the visitor's key over any platform-configured
one; `providers.resolve_model()` prefers their model choice over the curated per-role default for
**any** provider, not just the ones without one. Full live functionality — chat, diagnosis, voice
(where supported), image intake — runs against the visitor's own quota/billing.

Before the login form will navigate to the cockpit in this mode, it must have a non-empty key,
model, and (for `custom`) base URL, and `POST /providers/validate-key` must have returned `ok: true`
— either because the visitor pressed "Validate & Save Key" in the panel, or because `handleLogin`
ran that same check itself as a fallback. A missing or bad key surfaces the provider's real error
message inline and the visitor stays on the login screen; the key is never checked only on the
first live workflow run.

# Free Demo Key — operator-controlled shared key

Uses `providers.DEMO_PROVIDER` (`gemini`) with a key the OpsFlow operator controls
(`config.GEMINI_API_KEY`, a platform secret, never committed). Full live functionality, but shared
quota across every visitor using this mode — the same free-tier constraint that shaped
[Pregenerate Script](pregenerate-script.md)'s throttling. No model choice or validation step —
always Gemini's curated per-role map.

[^provider-mode-js]: frontend/src/lib/providerMode.js
[^main-py]: backend/main.py
[^login-mode-selector-jsx]: frontend/src/components/LoginModeSelector.jsx
