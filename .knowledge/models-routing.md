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
| Screenshot / error-image extraction | ~~Llama Vision~~ **gpt-4o** (substitute, 2026-08-07) | ~~`azure_ai/genailab-maas-Llama-3.2-90B-Vision-Instruct`~~ → `genailab-maas-gpt-4o` | Original deployment confirmed permanently gone (404/410); gpt-4o was fastest + most accurate of the tested candidates and is already `DEFAULT_CHAT_MODEL` — see decisions-log.md |
| Entity/PII detection in text, transcripts, extractions | Local SLM via Ollama (+ regex first pass) | see `ollama list` output, [env-network.md](env-network.md) | Highest-sensitivity content never leaves the machine |
| Incident narrative summarisation | gpt-4o-mini | `azure/genailab-maas-gpt-4o-mini` | High volume, low complexity, latency-sensitive |
| Ticket drafting, work notes, comments | gpt-4o-mini | `azure/genailab-maas-gpt-4o-mini` | Formatting-heavy, low reasoning demand |
| Embeddings (runbooks, postmortems, tickets, negative KB) | text-embedding-3-large | `azure/genailab-maas-text-embedding-3-large` | Only embedding model listed |
| Root-cause hypothesis generation & ranking | DeepSeek R1 | `azure_ai/genailab-maas-DeepSeek-R1` | Only step genuinely needing multi-step reasoning over conflicting evidence |
| Remediation / tuning plan drafting from runbooks | ~~DeepSeek V3~~ **gpt-4.1-nano** (substitute, 2026-08-07) | ~~`genailab-maas-DeepSeek-V3-0324`~~ → `azure/genailab-maas-gpt-4.1-nano` | Original deployment confirmed permanently gone (410); gpt-4.1-nano was fastest + reliably valid JSON of the tested candidates, and OpenAI's cheapest tier (matches "cheaper than R1" intent) — see decisions-log.md |
| Self-check / critique of the plan before the gate | gpt-4o-mini or local SLM | `azure/genailab-maas-gpt-4o-mini` | Verification gaps are a top failure category |
| Offline fallback for demo resilience | Local Ollama SLM | see `ollama list` | Must still run if the gateway dies mid-demo |
| Smoke-tested, unused in primary path | Phi ⚠ intermittent, see below | `azure_ai/genailab-maas-Phi-4-reasoning` | Handbook requires the smoke test; six of seven models genuinely used is the talking point |

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

## CONFIRMED UNREACHABLE (2026-08-07 smoke test)
- **`azure_ai/genailab-maas-Llama-3.2-90B-Vision-Instruct`** (Llama Vision, screenshot/error-image
  extraction role) — HTTP 404/410 (DeploymentNotFound / deprecated), re-checked twice, not
  transient. **RESOLVED:** human asked Claude to pick the best substitute; tested `gpt-4o-mini`,
  `gpt-4o`, `gpt-4.1-mini`, `gpt-4.1`, `gemini-2.5-flash`, `sonnet-4.6` against a real 64x64 PNG
  (a 1x1 pixel gets rejected by these providers as "unsupported image" — not a valid test). All
  passed except `gpt-4.1-mini` (misread color as "Pink"). Picked **`genailab-maas-gpt-4o`**:
  fastest correct response (975ms) and already `DEFAULT_CHAT_MODEL`, so no new routing surface.
  `backend/smoke_test.py`'s `VISION_MODEL` now points at it.
- **`genailab-maas-DeepSeek-V3-0324`** (DeepSeek V3, remediation/tuning plan drafting role) — HTTP
  410 `model_deprecated`, re-checked, not transient. **RESOLVED:** human asked Claude to pick the
  best substitute; tested `gpt-4o-mini`, `gpt-4.1-mini`, `gpt-4.1-nano`, `gemini-2.5-flash-lite`,
  `gemini-2.5-flash`, `Haiku-4.5` against a realistic structured-JSON remediation-plan prompt (not
  a trivial "ping" — this role needs valid structured output, not just reachability). Both Gemini
  models spent most of their token budget on hidden reasoning tokens and returned truncated/invalid
  JSON at a normal token budget — ruled out as unreliable for this role. Picked
  **`azure/genailab-maas-gpt-4.1-nano`**: fastest (1814ms) with valid JSON, and OpenAI's cheapest
  tier (matches the "cheaper than R1" intent behind V3's original placement). `backend/.env`
  `HANDBOOK_MODELS` updated to use it.

## INTERMITTENT (not a deprecation — do not substitute)
- **`azure_ai/genailab-maas-Phi-4-reasoning`** — 2026-08-07: passed 3 times earlier in the session,
  then failed once (404 DeploymentNotFound) in a later run. Rechecked 3x back-to-back: 404, 404,
  200. This is gateway-side flakiness (rolling deployment / capacity, not a removed model) — unlike
  Llama Vision and DeepSeek V3, which failed consistently on every recheck. **No substitute picked**
  — Phi is smoke-test-only per the handbook (not used in the primary routing path), so swapping it
  would defeat the point of testing this specific named model. Re-run `python smoke_test.py`
  close to the demo/submission checkpoint to catch it if it's still flaky then.
