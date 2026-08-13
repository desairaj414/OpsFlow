---
type: Module
title: LLM Provider Registry
description: backend/providers.py — the multi-provider LLM registry (Gemini default, OpenRouter fallback, TCS legacy/gated) with a per-role model map, replacing the original single-hardcoded-endpoint design.
resource: backend/providers.py
tags: [llm, config, providers]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: providers-py
    resource: backend/providers.py
    title: backend/providers.py
    last_modified: 2026-08-11
---

# Overview

`PROVIDERS: dict[str, dict]` holds one entry per LLM provider OpsFlow can talk to. Unlike a
single-`default_model`-per-provider design, each entry carries a `roles` map — `default`,
`reasoning`, `structured`, `vision` — because OpsFlow's agent chain calls distinct models for
distinct capability needs (see [Model Routing](model-routing.md)), not one general-purpose model
everywhere.[^providers-py]

# Schema

| Provider id | Label | Base URL | Vision | Transcription | SSL bypass |
|---|---|---|---|---|---|
| `gemini` | Google Gemini | `generativelanguage.googleapis.com/v1beta/openai/` | yes | no | no |
| `openrouter` | OpenRouter | `openrouter.ai/api/v1` | yes | no | no |
| `tcs` | TCS GenAI Lab (legacy, internal network only) | `config.BASE_URL` | yes | yes (Whisper) | yes |

Each entry also carries: `embedding_model` (or `None` — OpenRouter has no embeddings endpoint, and
embeddings never actually read this per-provider value at request time regardless, see
[Embeddings Fixed Provider](/decisions/embeddings-fixed-provider.md)), `key_hint` (shown in a
Bring Your Own Key UI), and for `tcs` a `note` warning it's gated and unreachable from the public
deploy.

# Roles

- `default` — general/summarization/self-check.
- `reasoning` — root-cause hypothesis generation (Diagnosis); needs genuine multi-step reasoning,
  tolerates higher latency.
- `structured` — remediation-plan drafting / chat filter-extraction; must return valid JSON
  reliably at a normal token budget (reasoning-heavy free models can burn the budget on hidden
  thinking tokens and truncate structured output — this shaped the actual model picks per role).
- `vision` — screenshot/error-image extraction.

`gemini`'s roles (`gemini-flash-lite-latest` for default/structured, `gemini-flash-latest` for
reasoning/vision) are Google's forward-compatible `-latest` aliases. `openrouter`'s roles are
`:free`-suffixed model ids — flagged in the code as an unverified placeholder registry (no live
`OPENROUTER_API_KEY` had been smoke-tested against these ids as of this bundle's writing) rather
than empirically confirmed the way the TCS substitutions were (see
[Model Routing](model-routing.md)).

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

# Consumers

[Provider Propagation](provider-propagation.md) (the per-request active-provider mechanism and
`api_client.py`'s `get_llm()`/`get_embeddings()`), the voice and vision intake paths (see
[Intake](/intake/)), and `scripts/pregenerate_demo_outputs.py` (see
[Pregenerate Script](/demo-modes/pregenerate-script.md)).

[^providers-py]: backend/providers.py
