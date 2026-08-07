---
type: reference
title: Extra Credit Backlog
status: draft
updated: 2026-08-07
related: [prd-phase-6.md, decisions-log.md]
---

From PRD §8, verbatim scope and sizing preserved exactly as the team decided. **Attempt ONLY after
the Phase 5 gate is green. Nothing here borrows from the core roadmap or the Final Phase — do not
reorder this priority list.**

## INCLUDE (attempt in this order if Phase 5 gate is green — highest ROI first)
1. **HTML quick-view launcher** (S) — one static `demo.html` with buttons to launch each scenario and jump to the right screen. Removes navigation fumbling on stage. **Highest ROI here per PRD.**
2. **Cost-per-incident meter** (S) — unit economics against a stated engineer-hour cost.
3. **Real-Jira portability wiring** (S) — **only if** the Phase 0 §4.21 probe to `atlassian.net` succeeded. Thirty seconds of demo showing an agent-created ticket in actual Jira.
4. **Self-consistency on root-cause ranking** (S) — sample N times, keep recurring hypotheses, report agreement rate.
5. **Prompt-injection resilience beat** (S) — surface the §6.2 adversarial log line as a named demo moment.
6. **Notification connectivity** (S) — approvals/summaries to a simulated channel.
7. **Change-risk classifier** (S–M) — CPU-trained tabular model over synthetic change history.
8. **Shift Handover Brief** (S–M) — one-click handover summary: open incidents, agent actions, pending approvals, refusals + reasons.
9. **Full eval harness** (L) — per-scenario accuracy, citation coverage, hallucination checks.

## SKIP — explicitly not built, with the reason (PRD §4.3, do not build these even with spare time)
- Multilingual intake — problem is machine-to-machine; inclusion effort went to voice accessibility instead.
- Real ServiceNow PDI — hibernation/licensing/waitlist risk on a restricted network; see [decisions-log.md](decisions-log.md).
- Real script execution against live infrastructure — simulated execution only, never implied real.
- ReAct-style open loops — turn caps instead, per the "more turns made it worse" finding.
- Real authentication — zero marginal credit, real cost; mock JWT + server-enforced role switcher stands.

## Cut-order if Phase 6 must be abandoned entirely
If Phase 5 overruns and Phase 6 is skipped, **that is fine and expected** — the Final Phase (freeze
& packaging, round-robin rehearsal) is never cut to make room for extra credit. See schedule in
[prd-phase-7-final.md](prd-phase-7-final.md).
