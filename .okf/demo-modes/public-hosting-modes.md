---
type: System
title: Public Hosting Modes
description: Three visitor-chosen ways to run OpsFlow — Instant Demo (zero live calls), Bring Your Own Key (visitor supplies a provider + key), and Free Demo Key (a Gemini key the operator controls) — replacing a design that only worked on the TCS corporate network.
tags: [demo, hosting, llm]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: provider-mode-js
    resource: frontend/src/lib/providerMode.js
    title: frontend/src/lib/providerMode.js
    last_modified: 2026-08-11
  - id: main-py
    resource: backend/main.py
    title: backend/main.py
    last_modified: 2026-08-11
---

# Overview

`frontend/src/lib/providerMode.js` persists one of three modes in `localStorage`:
`{mode: "instant_demo" | "byok" | "free_demo", provider, byokKey}`. Default is
`{mode: "free_demo", provider: "gemini", byokKey: null}`.[^provider-mode-js] Every request attaches
the active mode as headers (see [Provider Propagation](/architecture/provider-propagation.md)),
which the backend resolves into a `ProviderContext`.

# Instant Demo — zero live calls

When `X-LLM-Provider: instant_demo`, endpoints that would otherwise call a model instead read from
a pregenerated `data/demo_outputs.json` (built by [Pregenerate Script](pregenerate-script.md)).
`POST /workflows/run` looks up `f"{ci_id}:{workflow_type}"` and 400s with an explanatory message if
the requested combination isn't one of the pregenerated scenarios — a visitor gets a real,
previously-verified result with genuinely zero live model spend, at the cost of only covering the
handful of named scenarios.[^main-py] `POST /chat` and the voice/image intake endpoints similarly
short-circuit to an explanatory message rather than attempting a live call.

# Bring Your Own Key — visitor supplies provider + key

The visitor picks a provider (`gemini`/`openrouter`/`tcs`) and supplies their own API key, sent as
`X-LLM-Api-Key`. `providers.api_key_for()` prefers this key over any platform-configured one for
that provider. Full live functionality — chat, diagnosis, voice (where supported), image intake —
runs against the visitor's own quota/billing.

# Free Demo Key — operator-controlled shared key

Uses `providers.DEMO_PROVIDER` (`gemini`) with a key the OpsFlow operator controls
(`config.GEMINI_API_KEY`, a platform secret, never committed). Full live functionality, but shared
quota across every visitor using this mode — the same free-tier constraint that shaped
[Pregenerate Script](pregenerate-script.md)'s throttling.

# Known gap: no mode-selector UI yet

The plumbing for all three modes is complete on both backend and frontend, but as of this bundle's
writing there is no login-time mode-selector component in `frontend/src/components/` — see
[Cockpit UI](/architecture/cockpit-ui.md)'s "known gap" note. Every visitor currently gets the
default (`free_demo`, Gemini) until that UI is built.

[^provider-mode-js]: frontend/src/lib/providerMode.js
[^main-py]: backend/main.py
