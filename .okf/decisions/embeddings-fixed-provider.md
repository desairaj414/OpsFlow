---
type: Decision
title: Embeddings Stay Pinned to One Fixed Provider
description: Unlike chat/vision calls, embeddings never follow a visitor's per-session provider choice — they always use providers.EMBEDDING_PROVIDER, because every existing Chroma collection is indexed at one specific embedding model's vector dimension.
tags: [architecture, llm, embeddings, chroma]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: retrieval-py
    resource: backend/orchestrator/retrieval.py
    title: backend/orchestrator/retrieval.py
    last_modified: 2026-08-11
  - id: api-client-py
    resource: backend/api_client.py
    title: backend/api_client.py
    last_modified: 2026-08-11
---

# Decision

`orchestrator/retrieval.py`'s `_embed()` — the function [Enrichment](/agents/enrichment-agent.md)
and [Planner](/agents/planner-agent.md) actually call for RAG — always uses
`providers.EMBEDDING_PROVIDER` (pinned to `gemini`), regardless of the requesting visitor's chosen
provider/mode. `api_client.py`'s `get_embeddings()` follows the same pin and deliberately has no
per-request contextvar read, unlike `get_llm()`.[^retrieval-py]

# Alternatives considered

Let embeddings follow the same per-request provider a visitor's chat calls use, for consistency
with `get_llm()`'s behavior.

# Rationale

Every Chroma collection (`runbooks`, `postmortems`, `ticket_history`, `negative_kb`) is already
indexed with vectors from one specific embedding model, at that model's fixed dimension. A
query-time switch to a different provider's embedding model — even one available in the
[Provider Registry](/architecture/provider-registry.md) — would query with a different-dimension
vector against an already-indexed collection and raise Chroma's `InvalidDimensionException` on
every single query, confirmed by direct testing. That is a hard failure, not a graceful
degradation, so embeddings are deliberately treated as a fixed, server-controlled system operation
on a shared index rather than a per-visitor choice.[^retrieval-py] The same reasoning is why
`get_llm()`'s local-Ollama offline fallback (`.with_fallbacks()`) exists for chat calls but was
deliberately **not** wired into the live embeddings/retrieval path — Ollama's fallback embedding
model produces a different-dimension vector too.[^api-client-py]

# Consequence

A real cross-provider embeddings fallback would require a fully separate, Ollama-indexed
collection, not a same-collection swap — out of scope. `get_embeddings()`'s own
`enable_offline_fallback` parameter exists and is hand-rolled (`OpenAIEmbeddings` isn't a LangChain
`Runnable`, so it can't use `.with_fallbacks()` directly), but it is never actually invoked from the
live retrieval path for exactly this reason.

[^retrieval-py]: backend/orchestrator/retrieval.py
[^api-client-py]: backend/api_client.py
