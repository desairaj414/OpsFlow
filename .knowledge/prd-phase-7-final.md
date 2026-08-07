---
type: phase
title: "Phase 7 (FINAL) — Freeze & Packaging"
status: draft
updated: 2026-08-07
related: [arch-overview.md, citations.md, decisions-log.md, state-progress.md]
---

**Duration ~2h · H+19:00–21:00 · Sat 04:00–06:00 · FIXED, LAST, always run regardless of what Phase
6 did.** After this phase closes there is ~3.5h of slack before the hard **FEATURE FREEZE (Sat
09:30, H+24:30)** and **SUBMISSION (Sat 11:00, H+26:00)** — that slack is contingency/sleep, not
extra work time. **Feature work stops here. No exceptions.**

Owner: whole team — this phase is inherently collaborative (round-robin rehearsal needs everyone).

## Atomic steps
1. *(30 min)* Write `README.md`: gateway-vs-external statement (verbatim intent from PRD §0 — every
   model call goes to the TCS gateway or local Ollama, no external MaaS), "simulated systems"
   disclaimer (ITSM/Tracker/Monitoring/CMDB are our FastAPI mocks, not vendor SaaS), "MCP/A2A are
   open protocols running locally, call nothing outbound" line, and an honest note on what's
   simulated vs real (incl. the optional real-Jira probe if used). Pull provenance from [citations.md](citations.md).
2. *(25 min)* Architecture diagram (paste the tier diagram from [arch-overview.md](arch-overview.md) verbatim) + deck outline.
3. *(25 min)* Demo script with named beats, in order: alert-storm collapse opener → screenshot
   intake → voice-approved action → policy refusal → Drift-vs-Truth split screen → Fake Fix
   Detector catching a suppressed symptom → A→A′ learning → A2A delegation answer.
4. *(20 min)* Record a backup demo video; confirm the cached-response mode (Phase 5) works standalone in case the gateway is down at judging time.
5. *(20 min)* **Round-robin rehearsal: all team members explain the full flow end to end.** Named explicitly in the PRD's guidance-block coverage — cheapest marks available, do not skip.

## Files created/modified
`README.md`, `data/PROVENANCE.md` (finalize), deck file (format TBD — confirm against handbook
submission requirements, PRD §9 open question), demo script doc, backup video file.

## [MOCK-P1] markers
README must explicitly enumerate every [MOCK-P1] item from Phases 1-6 — pull the list from each
phase node's "[MOCK-P1] markers" section rather than re-deriving it.

## Hard acceptance criteria
- [ ] README contains all four required disclaimers (gateway-vs-external, simulated-systems, MCP/A2A-local, simulated-vs-real honesty note)
- [ ] Architecture diagram present and matches [arch-overview.md](arch-overview.md) exactly
- [ ] Demo script written with all 8 named beats in order
- [ ] Backup video recorded and playable; cached-response mode confirmed working offline
- [ ] Every team member has completed the round-robin rehearsal at least once
- [ ] Submission format (notebook/README/deck structure) confirmed against the handbook — PRD §9 flags this as an open question, resolve it here if still open

## CONTEXT CHECKPOINT — update on completion (this is the last checkpoint before freeze)
- [.knowledge/state-progress.md](state-progress.md) — CURRENT PHASE → "Freeze — submission ready", H+ HOURS ELAPSED, RESUME INSTRUCTION updated for the judging session
- [.knowledge/decisions-log.md](decisions-log.md) — append any last-minute decisions made during packaging (e.g. what got cut)
- [.knowledge/citations.md](citations.md) — confirm every dataset/model row is filled in before README is finalized from it
