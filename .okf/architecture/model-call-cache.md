---
type: Module
title: Model-Call Cache
description: hash(prompt_version, exact prompt text) -> response cache for the two decision-critical agent LLM calls (Diagnosis, Planner), backed by a SQLite table that existed in the schema since Phase 1 but was never written to until this concept was built.
resource: backend/orchestrator/cache.py
tags: [reliability, cost, agents]
status: stable
generated: { by: "claude-sonnet-5/okf-maintain", at: "2026-08-17T00:00:00Z" }
sources:
  - id: cache-py
    resource: backend/orchestrator/cache.py
    title: backend/orchestrator/cache.py
    last_modified: 2026-08-17
  - id: diagnosis-py
    resource: backend/agents/diagnosis.py
    title: backend/agents/diagnosis.py
    last_modified: 2026-08-17
  - id: planner-py
    resource: backend/agents/planner.py
    title: backend/agents/planner.py
    last_modified: 2026-08-17
---

# Overview

[Diagnosis](/agents/diagnosis-agent.md) and [Planner](/agents/planner-agent.md) both call their LLM
at `temperature=0` specifically for reproducibility — the same evidence should always produce the
same hypothesis/plan. Caching an exact-match input is a direct extension of that existing design
goal, not a deviation from it: a replayed [scenario](/data/database-schema.md) (via the Scenario
Launcher UI, [the eval harness](/architecture/eval-harness.md), or
[the pregenerate script](/demo-modes/pregenerate-script.md)) can return the same, already-verified
answer without a live gateway call.[^cache-py]

The cache key is `sha256(prompt_version + "|" + exact_prompt_text)`, stored in the `model_call_cache`
table ([Database Schema](/data/database-schema.md)) alongside the response text, token count,
latency, and the model id that actually answered. `prompt_version` is a per-agent constant
(`diagnosis-v1`, `planner-v1`) bumped whenever that agent's prompt template changes, so an old cache
row can never silently leak into a differently-worded prompt.[^cache-py]

# Retry-safety

Both agents retry their LLM call on a JSON-parse failure ([Turn Caps](/agents/supervisor.md)). A
retry's whole point is a fresh sample after a bad one, so the cache is only **checked** on the first
attempt — checking it again on a retry would just replay the same failure (or the same miss)
forever. The cache is only **stored to** once a response actually parses successfully, so a failed
attempt never poisons the cache for a future replay.[^diagnosis-py][^planner-py]

# Deliberately not wired everywhere

`main.py`'s two chat call sites (`_classify_chat_intent`, `_chat_app_help`) do **not** use this
cache — they're free-form user text that varies on nearly every message, so an exact-match cache
would almost never hit, and the reproducibility argument above doesn't apply to them the way it
does to the decision-critical agent chain.[^cache-py]

# Measured

A real consecutive replay of all 14 seeded scenarios via
[the eval harness](/architecture/eval-harness.md) hit the cache on 18/28 checks (both agents' calls,
across all scenarios) on the second pass. The remaining misses are consistent with
[Chroma](/data/database-schema.md)'s approximate-nearest-neighbor retrieval returning
slightly different precedent-evidence ordering run-to-run (a known characteristic of that vector
search, not a defect in the cache key construction) — Diagnosis's prompt includes the enrichment
evidence block verbatim, so a reordered precedent hit changes the exact prompt text and therefore
the cache key.

[^cache-py]: backend/orchestrator/cache.py
[^diagnosis-py]: backend/agents/diagnosis.py
[^planner-py]: backend/agents/planner.py
