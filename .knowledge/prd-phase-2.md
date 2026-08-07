---
type: phase
title: "Phase 2 — Deterministic Core (no LLM)"
status: done
updated: 2026-08-07
related: [domain-guardrails.md, domain-privacy.md, domain-multimodal-intake.md, schema-db.md, prd-phase-3.md]
---

**Duration ~2h · H+4:30–6:30 · Fri 13:30–15:30.**
Deliberately built before any agent work — everything else validates against this layer, and it's
the layer that still works when models misbehave. Owner: **Person C — Deterministic Core.**

## Atomic steps
1. *(30 min)* Correlation engine: fingerprint + time-window + topology clustering over the alert stream (scikit-learn, no LLM per [arch-overview.md](arch-overview.md) routing principle). Files: `backend/correlation/cluster.py`.
2. *(30 min)* Policy gate (pure Python rule engine): change-freeze windows, prod vs non-prod, CI criticality, blast-radius threshold, max concurrent changes, required-approver role. Unit-tested. Files: `backend/guardrails/policy_gate.py`, `backend/tests/test_policy_gate.py`.
3. *(20 min)* Blast-radius computation from the CMDB adjacency table. Files: `backend/guardrails/blast_radius.py`.
4. *(20 min)* Append-only audit log write path per [schema-db.md](schema-db.md) `audit_log` table. Files: `backend/orchestrator/audit.py`.
5. *(30 min)* Voice intent parser — closed-vocabulary matcher for the 6 intents in [domain-multimodal-intake.md](domain-multimodal-intake.md). No LLM. Files: `backend/intake/voice_intent.py`.
6. *(30 min)* PII/secret scrubber + reversible tokenisation (regex first pass + local-SLM name detection) + unit tests against `pii_ground_truth.json`. Files: `backend/guardrails/scrubber.py`, `backend/tests/test_scrubber.py`.

## Files created/modified
`backend/correlation/cluster.py`, `backend/guardrails/{policy_gate,blast_radius,scrubber}.py`,
`backend/orchestrator/audit.py`, `backend/intake/voice_intent.py`, `backend/tests/test_*.py`.

## [MOCK-P1] markers
None — this layer is real code, not stubbed, by design (it must be provably consistent).

## Hard acceptance criteria (re-verify, don't just write)
- [x] Feeding the synthetic alert storm (Phase 1 data, 500 alerts) through the correlation engine reproducibly collapses it into 420 candidate clusters across 10 topology groups (same input → same output, verified via 2 identical runs)
- [x] Policy gate unit tests green (12/12), covering at least: freeze-window block, prod-vs-non-prod, blast-radius-above-threshold, missing-approver-role — plus blast-radius-block-threshold, max-concurrent-changes, and the advisory-only-tuning rule
- [x] Blast-radius computation returns correct CI counts against known CMDB adjacency fixtures (9/9 unit tests, hand-built chain + star topology fixtures)
- [x] Audit log writes are append-only — enforced by a real SQLite trigger (not just no update/delete function in the module; a raw SQL UPDATE/DELETE is rejected by the DB itself), every write captures actor/action/target/timestamp/evidence/model/approval/modality (5/5 unit tests)
- [x] Voice intent parser correctly matches all 6 supported intents and explicitly rejects/flags anything outside the closed vocabulary, never silently guesses (11/11 unit tests, incl. near-miss and misheard-fragment cases)
- [x] Scrubber unit tests green (7/7) against `pii_ground_truth.json` (31 planted items), reversible tokenisation confirmed round-trip. Measured: 100% recall on regex-covered types, 100% recall on local-SLM person names (this run), adversarial injection line correctly flagged with zero false positives — see [domain-privacy.md](domain-privacy.md) for the full numbers.

## CONTEXT CHECKPOINT — update on completion
- [.knowledge/domain-guardrails.md](domain-guardrails.md) — confirm policy gate + Fake-Fix-Detector prerequisites are in place (verification agent in Phase 3 depends on the audit/scrubber plumbing here)
- [.knowledge/domain-privacy.md](domain-privacy.md) — record actual scrubber precision/recall from the `pii_ground_truth.json` run
- [.knowledge/state-progress.md](state-progress.md) — CURRENT PHASE → Phase 3, DONE list, FILE INVENTORY
- [.knowledge/errors-solved.md](errors-solved.md) — log any scikit-learn/regex edge cases hit
