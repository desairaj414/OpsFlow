---
type: phase
title: "Phase 0 — Environment & Gateway Smoke Test"
status: active
updated: 2026-08-07
related: [env-network.md, models-routing.md, state-progress.md, prd-phase-1.md]
---

**Duration 1.5h (incl. optional 30min probe) · H+0:00–1:30 · Fri 09:00–10:30 · FIXED, FIRST, parallel with any remaining discussion.**
Owner: whichever team member is free first (infra/env role) — this phase is not parallelizable with itself.

## Atomic steps
1. *(15 min)* Run `ollama list`; record exact model names + sizes in `PHASE0_FINDINGS.md`. **Never download a new model.**
2. *(45 min, BLOCKING)* Call every handbook-listed model once through the gateway: `gpt-4o-mini`, DeepSeek V3, DeepSeek R1, **Whisper**, **Llama Vision**, Phi, `text-embedding-3-large`. Use actual `.env` ids from [env-network.md](env-network.md). **Whisper and Llama Vision are blocking — if either fails, escalate immediately, don't wait until tonight (PRD §2.4 depends on both).**
   Files: `backend/smoke_test.py`.
3. *(15 min)* Confirm the SSL bypass (`verify=False`) and `TIKTOKEN_CACHE_DIR` fix are active and working. Files: `backend/config.py`.
4. *(30 min)* Record latency + token cost per model called in step 2, in `PHASE0_FINDINGS.md`.
5. *(30 min)* Verify `text-embedding-3-large` → Chroma round-trip end to end (embed one string, store, query it back).
6. *(45 min)* Confirm repo scaffold: FastAPI skeleton, frontend skeleton, SQLite schema stub, module folders per [rules-backend.md](rules-backend.md). Most of this already exists — verify, don't rebuild.
7. *(30 min, OPTIONAL, hard-timeboxed)* Check if the lab network reaches `atlassian.net`. If yes, create the free Jira instance + one API token, record both, **stop — do not wire anything yet.** If no, abandon permanently, do not retry later.
8. *(15 min)* Write/finalize `PHASE0_FINDINGS.md` at repo root.

## Files created/modified
- `PHASE0_FINDINGS.md` (new, repo root)
- `backend/smoke_test.py`, `backend/config.py` (verify only, already exist)
- `.knowledge/env-network.md` (fill smoke-test results table)

## [MOCK-P1] markers
None — this phase touches only the real gateway and real local Ollama. No simulated systems yet.

## Hard acceptance criteria (must be RE-VERIFIED, not just written, before Phase 1 starts)
- [ ] `ollama list` output recorded in `PHASE0_FINDINGS.md`
- [ ] All 7 handbook models confirmed reachable via the gateway, **including Whisper and Llama Vision explicitly**
- [ ] SSL bypass + `TIKTOKEN_CACHE_DIR` fix confirmed working (not just present in code)
- [ ] Latency + token cost per model recorded
- [ ] `text-embedding-3-large` → Chroma round-trip confirmed working
- [ ] Repo scaffold confirmed present and running (backend boots, frontend boots)
- [ ] `PHASE0_FINDINGS.md` exists and is complete
- [ ] Jira probe attempted within its 30-minute cap and its outcome recorded (success or abandoned)

## CONTEXT CHECKPOINT — update on completion
- [.knowledge/env-network.md](env-network.md) — fill in the smoke-test results table
- [.knowledge/state-progress.md](state-progress.md) — move CURRENT PHASE to Phase 1, update H+ HOURS ELAPSED, LAST VERIFIED STEP
- [.knowledge/models-routing.md](models-routing.md) — flag any model found unreachable (do not silently substitute)
- [.knowledge/citations.md](citations.md) — confirm the model-id table matches what was actually verified reachable
