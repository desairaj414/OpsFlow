---
type: phase
title: "Phase 6 — Extra Credit (conditional)"
status: draft
updated: 2026-08-07
related: [extra-credit.md, prd-phase-5.md, prd-phase-7-final.md]
---

**Duration ≤1.5h · H+17:30–19:00 · Sat 02:30–04:00 · CONDITIONAL on a green Phase 5 gate.**
Hard stop at H+19:00 regardless of progress. **Borrows nothing from the Final Phase — if this
phase is skipped entirely because Phase 5 ran long, that is the correct outcome, not a failure.**
Owner: whoever is free first after Phase 5 closes.

## Atomic steps
Pull from [extra-credit.md](extra-credit.md) **in the exact priority order listed there** — do not
reorder based on personal preference. Each item is sized S (≤45 min) or S-M unless already marked L
(skip L items in this phase, see extra-credit.md item 9).
1. *(≤45 min)* HTML quick-view launcher (`demo.html`) — highest ROI per PRD, attempt first.
2. *(≤45 min, if time remains)* Cost-per-incident meter.
3. *(≤30 min, if time remains AND Phase 0's Jira probe succeeded)* Real-Jira portability wiring.
4. *(remaining time)* Continue down the [extra-credit.md](extra-credit.md) INCLUDE list in order; stop the instant H+19:00 arrives, mid-item is fine to abandon.

## Files created/modified
Varies per item attempted — see [extra-credit.md](extra-credit.md) for scope of each. Do not create
files for SKIP items even if time remains — see extra-credit.md's SKIP list, those are final.

## [MOCK-P1] markers
Whatever is attempted here remains subject to the same [MOCK-P1] rules as its originating phase
(e.g. real-Jira wiring is the one deliberate exception — it is optional and external, must be
labelled on screen as such per PRD §4.21).

## Acceptance criteria
This phase has no hard gate — it is pure upside, time-boxed. The only rule that matters:
- [ ] Hard stop respected at H+19:00 (Sat 04:00) even if an item is mid-completion
- [ ] Nothing attempted here regressed anything verified in Phases 0-5 (re-run the Phase 5 double-pass check if anything shared code was touched)

## CONTEXT CHECKPOINT — update on completion (or on hard stop, whichever comes first)
- [.knowledge/extra-credit.md](extra-credit.md) — mark which items were attempted/completed/abandoned mid-way
- [.knowledge/state-progress.md](state-progress.md) — CURRENT PHASE → Phase 7 (Final), FILE INVENTORY additions
