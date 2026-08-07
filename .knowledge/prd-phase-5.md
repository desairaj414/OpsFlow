---
type: phase
title: "Phase 5 — Scenario Library, Eval & Hardening"
status: draft
updated: 2026-08-07
related: [domain-workflows.md, domain-guardrails.md, domain-privacy.md, prd-phase-6.md, prd-phase-7-final.md]
---

**Duration ~2.5h · H+15:00–17:30 · Sat 00:00–02:30.** Owner: **Person G — Eval/Hardening**, all hands for the final double-run.

## Atomic steps
1. *(30 min)* Build remaining scenario fixtures to reach 10-12 total (PRD §6.1), covering all 3 workflow families, using the data from Phase 1. Files: `data/scenarios/*.json`, rows in `scenarios` table ([schema-db.md](schema-db.md)).
2. *(25 min)* Edge-case scenarios: conflicting evidence, no strong precedent, policy refusal, scrubber catch, CMDB drift, prompt-injection line (PRD §6.2 adversarial log line). Files: `data/scenarios/edge_*.json`.
3. *(20 min)* Add ≥2 deliberately noisy/accented voice samples and ≥1 low-quality/legacy-UI screenshot fixture (proves the §2.5 bias mitigations aren't just claimed). Files: `data/voice_samples/*.wav`, `data/screenshots/*.png`.
4. *(30 min)* Eval harness: per-scenario pass/fail, `verified_resolved` vs `symptom_suppressed` counts, citation coverage. Files: `backend/eval/harness.py`.
5. *(20 min)* Wire the model-call cache (`hash(prompt_version, scrubbed_input) → response`) into every agent call, confirm a replayed scenario doesn't re-hit the gateway. Files: `backend/orchestrator/cache.py`.
6. *(15 min)* Confirm the offline/local-Ollama fallback path works if the gateway is unreachable.
7. *(10 min)* Full run of every scenario — pass 1.
8. *(10 min)* Full run of every scenario — pass 2, consecutively. **Anything flaky here gets cut from the demo, not debugged at 2am.**

## Files created/modified
`data/scenarios/*.json`, `data/voice_samples/*`, `data/screenshots/*`, `backend/eval/harness.py`,
`backend/orchestrator/cache.py`.

## [MOCK-P1] markers
None new — this phase hardens what Phases 1-3 built.

## Hard acceptance criteria — this is the gate to Phase 6/7, not optional
- [ ] 10-12 named scenarios exist, covering incident/patch/performance
- [ ] All PRD §6.2 edge cases represented (conflicting evidence, no precedent, policy refusal, scrubber catch, drift, prompt-injection line)
- [ ] ≥2 noisy/accented voice fixtures and ≥1 low-quality screenshot fixture exist and are exercised by a scenario
- [ ] Eval harness reports pass/fail, verified-resolved vs symptom-suppressed, and citation coverage per scenario
- [ ] Cache confirmed working (replay does not re-call the gateway)
- [ ] Offline fallback confirmed: a scenario runs (possibly degraded) with the gateway disconnected
- [ ] **Every scenario passes twice, consecutively.** Anything that doesn't is cut from Phase 6/7 scope, not fixed under time pressure

## CONTEXT CHECKPOINT — update on completion
- [.knowledge/state-progress.md](state-progress.md) — CURRENT PHASE → Phase 6 (or 7 if 6 is skipped), record which scenarios were cut for flakiness
- [.knowledge/citations.md](citations.md) — add voice/screenshot fixtures to the dataset table with generator/date
- [.knowledge/domain-privacy.md](domain-privacy.md) — record actual scrubber precision/recall from the full scenario run
