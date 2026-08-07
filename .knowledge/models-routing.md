---
type: reference
title: Model Routing Table
status: active
updated: 2026-08-07
related: [arch-overview.md, citations.md, env-network.md]
---

From PRD §3.2, mapped to actual `.env` model ids (see `backend/.env` → `MODELS`).

## Routing table
| Task | Model (handbook name) | Actual `.env` id | Why |
|---|---|---|---|
| Alert normalisation, dedup, correlation clustering | **No LLM** — Python + scikit-learn | n/a | Deterministic, fast, reproducible, explainable |
| Policy gate, blast radius, scheduling constraints | **No LLM** — rule engine | n/a | Must be auditable and provably consistent |
| Voice transcription | Whisper | `azure/genailab-maas-whisper` (alt `azure/gpt-realtime-whisper`) | Purpose-built, only speech model listed |
| Voice intent parsing | **No LLM** — closed-vocabulary matcher | n/a | A misheard command must never become an unintended action |
| Screenshot / error-image extraction | Llama Vision | `azure_ai/genailab-maas-Llama-3.2-90B-Vision-Instruct` | Only vision model listed |
| Entity/PII detection in text, transcripts, extractions | Local SLM via Ollama (+ regex first pass) | see `ollama list` output, [env-network.md](env-network.md) | Highest-sensitivity content never leaves the machine |
| Incident narrative summarisation | gpt-4o-mini | `azure/genailab-maas-gpt-4o-mini` | High volume, low complexity, latency-sensitive |
| Ticket drafting, work notes, comments | gpt-4o-mini | `azure/genailab-maas-gpt-4o-mini` | Formatting-heavy, low reasoning demand |
| Embeddings (runbooks, postmortems, tickets, negative KB) | text-embedding-3-large | `azure/genailab-maas-text-embedding-3-large` | Only embedding model listed |
| Root-cause hypothesis generation & ranking | DeepSeek R1 | `azure_ai/genailab-maas-DeepSeek-R1` | Only step genuinely needing multi-step reasoning over conflicting evidence |
| Remediation / tuning plan drafting from runbooks | DeepSeek V3 | `genailab-maas-DeepSeek-V3-0324` | Structured generation, cheaper than R1 |
| Self-check / critique of the plan before the gate | gpt-4o-mini or local SLM | `azure/genailab-maas-gpt-4o-mini` | Verification gaps are a top failure category |
| Offline fallback for demo resilience | Local Ollama SLM | see `ollama list` | Must still run if the gateway dies mid-demo |
| Smoke-tested, unused in primary path | Phi | `azure_ai/genailab-maas-Phi-4-reasoning` | Handbook requires the smoke test; six of seven models genuinely used is the talking point |

## Rehearsed trade-offs (PRD §3.3) — see also [arch-overview.md](arch-overview.md)
- R1 costs latency (tens of seconds) — one step only, async, UI streams progress.
- Higher turn counts ≠ better (ITBench) — hard turn caps and explicit termination conditions per agent.
- Whisper/Llama Vision latency is confined to intake, never the main loop.
- Local SLMs are weaker — narrow tasks only (extraction, classification, redaction).
- Log tokens + wall-clock per agent step; render it — this is a graded artifact, not a footnote.

## Do not re-decide
This mapping is fixed by PRD §3.2/§3.3. If Phase 0's smoke test finds a model unreachable, that is a
finding to log in [env-network.md](env-network.md) and escalate to the human — do not silently
substitute a different model without recording why.
