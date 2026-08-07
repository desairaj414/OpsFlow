# Phase 0 Findings — Environment & Gateway Smoke Test

Verified 2026-08-07, H+0:00–H+2:50 (Fri 09:00–11:50). See `.knowledge/prd-phase-0.md` for the
atomic step list this satisfies, `.knowledge/env-network.md` for the full results table, and
`.knowledge/models-routing.md` / `.knowledge/decisions-log.md` for the model-substitution record.

## 1. Local Ollama models (`ollama list`)
Pre-installed, none pulled:
| Model | Size |
|---|---|
| devstral:latest | 14 GB |
| qwen-2.5.1-coder-it:latest | 4.7 GB |
| llama-3.2-3b-it:latest | 2.0 GB |
| gemma-3-4b-it:latest | 2.5 GB |
| deepseek-r1:latest | 4.7 GB |
| gte-large:latest | 358 MB |

## 2. Handbook models — reachability, latency, token cost
Tested via `backend/smoke_test.py` (default fast mode: `HANDBOOK_MODELS`, 4 chat calls + 3
dedicated blocking checks — see that file's docstring for why the full 32-model `MODELS` sweep is
`--full`-only).

| Model (handbook role) | Result | Latency | Notes |
|---|---|---|---|
| gpt-4o-mini (narrative/ticket/self-check) | ✅ PASS | ~870-1020ms | stable across runs |
| DeepSeek R1 (root-cause hypothesis) | ✅ PASS | ~820-1400ms | stable across runs |
| Whisper (voice intake) | ✅ PASS | 633-1581ms | real audio upload → real transcript, not just reachability |
| Embedding → Chroma round-trip | ✅ PASS | 330-433ms | `text-embedding-3-large`, dim=3072, embed→store→query matched |
| ~~Llama Vision~~ → **gpt-4o** (screenshot/error-image extraction) | ✅ PASS (substitute) | 904-1323ms | original deployment permanently gone (404/410 DeploymentNotFound/deprecated, confirmed on 2 rechecks) |
| ~~DeepSeek V3~~ → **gpt-4.1-nano** (remediation/tuning plan drafting) | ✅ PASS (substitute) | 1206-1814ms | original deployment permanently gone (410 deprecated, confirmed on recheck); substitute validated against a realistic structured-JSON plan-drafting prompt, not just a ping |
| Phi-4-reasoning (handbook smoke-test requirement, unused in primary path) | ⚠ INTERMITTENT | n/a | passed 3x, then failed, rechecked 3x back-to-back: 404, 404, 200 — gateway-side flakiness, not a deprecation. Non-blocking; re-check before the demo/submission checkpoint |

**Two permanent model substitutions were made this session** (both delegated to Claude by the
human after confirming the originals were genuinely, consistently unreachable — not a silent
substitution):
- **Vision path:** `azure_ai/genailab-maas-Llama-3.2-90B-Vision-Instruct` → `genailab-maas-gpt-4o`.
  Chosen from 6 candidates tested against a real 64x64 test image (a 1x1 pixel is rejected by
  these providers as "unsupported image" — not a valid test); gpt-4o was fastest with a correct
  answer and is already `DEFAULT_CHAT_MODEL`.
- **Remediation/tuning drafting:** `genailab-maas-DeepSeek-V3-0324` → `azure/genailab-maas-gpt-4.1-nano`.
  Chosen from 6 candidates tested against a realistic structured-JSON remediation-plan prompt; the
  two Gemini candidates spent most of their token budget on hidden reasoning tokens and returned
  truncated/invalid JSON at a normal budget, ruling them out.

Full rationale and rejected alternatives: `.knowledge/decisions-log.md`.

## 3. SSL bypass & TIKTOKEN_CACHE_DIR
Both confirmed live-working (not just present in code) — every gateway call above succeeded
through the corporate proxy, and `backend/token/` is populated from the tiktoken pre-cache step.

## 4. Repo scaffold
- Backend: `uvicorn main:app --host 0.0.0.0 --port 8765` boots clean, `/health` → `200 {"status":"ok"}`.
- Frontend: `npm.cmd run dev` (Vite, port 3000) boots clean, `200 OK` on `/`.
- Both re-verified after this session's `requirements.txt` and `.env` changes (chromadb,
  scikit-learn, pandas, numpy, faker, mcp added; `HANDBOOK_MODELS` added).
- **Known deviation:** frontend is Vite/React; PRD specifies Next.js. Human decision 2026-08-07:
  migrate to Next.js. Migration deferred to Phase 4 (Cockpit UI) — Phase 0/1 are backend-only, so
  this was not done as emergency surgery on the working Vite skeleton. See `.knowledge/decisions-log.md`.

## 5. Jira portability probe (PRD §4.21, optional, 30-min hard cap)
Network reachability confirmed: `https://www.atlassian.net` → HTTP 302 (redirects to login), so
the lab network is not blocking it. **Instance creation itself was not attempted** — creating a
real Jira Cloud site requires manual signup (email verification, site naming, ToS acceptance),
which is a human action, not something to automate. Deferred to the human; not wired into anything
per the PRD's explicit "stop — do not wire anything yet" instruction regardless.

## Outcome
Phase 0 acceptance criteria (`.knowledge/prd-phase-0.md`) are satisfied:
- [x] `ollama list` recorded
- [x] All 7 handbook models confirmed reachable (2 via human-approved substitutes; 1 intermittent but non-blocking)
- [x] SSL bypass + TIKTOKEN_CACHE_DIR confirmed working
- [x] Latency + token cost per model recorded
- [x] `text-embedding-3-large` → Chroma round-trip confirmed
- [x] Repo scaffold confirmed present and running (backend + frontend both re-booted clean)
- [x] This file
- [x] Jira probe attempted within its 30-min cap, outcome recorded (reachable, signup deferred to human)

**Phase 0 is closed.** Proceeding to Phase 1 (`.knowledge/prd-phase-1.md`).
