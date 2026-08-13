---
type: Decision
title: Multi-Provider Architecture for Public Hosting
description: Replaced the single hardcoded TCS GenAI Lab endpoint with a provider registry (Gemini default, OpenRouter fallback, TCS kept as a gated legacy option) so OpsFlow can run as a public, self-serve demo instead of only on the TCS corporate network.
tags: [architecture, llm, hosting]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: providers-py
    resource: backend/providers.py
    title: backend/providers.py
    last_modified: 2026-08-11
  - id: models-routing
    resource: .knowledge/models-routing.md
    title: Model Routing Table
    last_modified: 2026-08-07
---

# Decision

Introduced [Provider Registry](/architecture/provider-registry.md) — Gemini as the default/free
provider, OpenRouter as a fallback, and the original TCS GenAI Lab endpoint retained as a legacy,
gated option — plus [Provider Propagation](/architecture/provider-propagation.md), the per-request
mechanism that lets a visitor's choice reach every LLM call site via HTTP headers and a contextvar,
instead of a compile-time constant.

# Alternatives considered

Keep the app reachable only via the original single-endpoint design and note the public-hosting
limitation in the README instead of building provider abstraction.

# Rationale

The original design hardcoded `genailab.tcs.in` — reachable only from the TCS corporate network,
using a TCS-issued key — as the sole provider for every LLM call. That is workable for an on-site
hackathon demo but breaks entirely for a public, self-serve deploy: there is no reachable backend
and no key a visitor outside that network could use. Gemini was chosen as the default because its
free tier covers both chat and vision with a single key and is OpenAI-compatible, so the existing
`ChatOpenAI`-based plumbing needed parameterizing rather than a rewrite. TCS was kept, not deleted,
so the app can still run against the original endpoint on that network — it just isn't the default,
and its endpoint-specific workaround (`needs_ssl_bypass`) is now conditional per-provider rather
than a global, always-on monkeypatch (see `backend/config.py`'s `TCS_NETWORK` gate).

# Consequence

Every call site that used to read a fixed model constant now resolves its model from
`provider_cfg["roles"][role]` (see [Provider Registry](/architecture/provider-registry.md)) — there
is no more single "the" model per task the way `.knowledge/models-routing.md` originally described;
that document's task-to-model-id table describes the pre-refactor state and should be read
skeptically against the current code (see [Model Routing](/architecture/model-routing.md) for the
routing *principle*, which still holds).[^models-routing]

[^models-routing]: Model Routing Table
