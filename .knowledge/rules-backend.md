---
type: rules
title: Backend Rules & Commenting Standard
status: active
updated: 2026-08-07
related: [rules-frontend.md, architecture/architecture/arch-overview.md, reference/reference/env-network.md]
---

**Re-read this on every coding step. It is a standing rule, not a one-time reminder.**

## Code commenting standard (PRD §0 — Handbook §8.5 grades this, verbatim)
- Every function / module: **one short purpose comment** (what it is for, not what each line does).
- Inline comments explain **WHY**, reserved for non-obvious logic: regex patterns, routing
  thresholds, confidence cut-offs, guardrail conditions, correlation window sizes, chunk-boundary
  rules, MCP/A2A schema choices.
- **No line-by-line narration of obvious code.** `# increment counter` is worse than no comment.
- One responsibility per module.

## Module layout (PRD §0)
`agents/`, `adapters/`, `mcp_servers/`, `guardrails/`, `orchestrator/`, `intake/`, `chunking/`, `eval/`.
Create these under `backend/` as each phase needs them — do not pre-create empty stubs for phases not yet started.

## Honesty rule — non-negotiable (PRD §0)
Lab machines are CPU-only. **We have not trained or fine-tuned any LLM and will never say we have.**
Our work is: prompting, model routing, RAG, deterministic rule engines, protocol implementation,
and — only where genuinely executed — lightweight classical ML trained on CPU (scikit-learn
scale). If a docstring, log message, or README line implies fine-tuning, it is a bug — fix it.

## Network fixes — mandatory on every entrypoint
See [env-network.md](reference/env-network.md) for the exact code: `TIKTOKEN_CACHE_DIR` set before any
tiktoken-dependent import; `httpx.AsyncClient(verify=False)` (async — PRD §0 mandates FastAPI async)
for all gateway calls; `requests.Session` patched too (tiktoken's downloader ignores the ssl monkeypatch).

## Deterministic-vs-LLM routing rule (PRD §3.1 — enforce in code review)
Before writing any function that calls a model, ask: is this deterministic? If yes (correlation,
policy gate, blast radius, voice-intent parsing, metric math, scheduling constraints), **it must be
plain Python / scikit-learn, never an LLM call.** This is graded and a common hackathon mistake.

## Framework-neutrality
No LangGraph/CrewAI/AutoGen (see [decisions-log.md](decisions-log.md)). Agents are plain typed
Python classes/functions orchestrated by the Supervisor; MCP and A2A provide the interop a
framework would otherwise give.

## Async & FastAPI
- All I/O-bound endpoints and model calls are `async def`, using `httpx.AsyncClient`.
- Every MCP server is its own FastAPI (or MCP-native) process — see [domain-agents.md](domain/domain-agents.md) and the relevant phase node for exact ports.

## Where to look before writing backend code
- Canonical schemas: [api-contract.md](architecture/api-contract.md) (frozen at end of Phase 1 — do not invent new shapes after freeze).
- DB schema: [schema-db.md](architecture/schema-db.md).
- Model choice for a given task: [models-routing.md](architecture/models-routing.md).
- Guardrail behaviour required: [domain-guardrails.md](domain/domain-guardrails.md).
