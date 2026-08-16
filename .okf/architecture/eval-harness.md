---
type: Module
title: Eval Harness
description: Runs every seeded Scenario Library fixture through the real run_workflow() and grades the outcome against each fixture's expected block — pass/fail, verified_resolved vs symptom_suppressed counts, citation coverage, and model-call-cache hit rate.
resource: backend/eval/harness.py
tags: [eval, testing, scenarios]
status: stable
generated: { by: "claude-sonnet-5/okf-maintain", at: "2026-08-17T00:00:00Z" }
sources:
  - id: harness-py
    resource: backend/eval/harness.py
    title: backend/eval/harness.py
    last_modified: 2026-08-17
---

# Overview

`python -m eval.harness [run_label]` reads every row in the `scenarios` table
([Database Schema](/data/database-schema.md)), re-opens each one's `fixture_path` JSON for its
`ci_id`/`alert_category`/`auto_approve`/`expected` fields, and runs it through the exact same
`run_workflow()` [Supervisor](/agents/supervisor.md) entry point the Scenario Launcher UI panel and
[the pregenerate script](/demo-modes/pregenerate-script.md) already use — not a fourth
reimplementation of "how to run a scenario."[^harness-py]

# Grading

Only asserts on keys a fixture's `expected` block actually declares (`status` and/or
`verification_status`); each may be a single value (exact match) or a list (any-of). Fixture keys
ending in `_note` are informational context for a human, never asserted — several edge-case fixtures
(conflicting evidence, no strong precedent) are LLM-dependent and deliberately soft-graded rather
than forced to a specific outcome.[^harness-py]

# Report

Writes `data/eval_report.json`: total/passed/failed, `verified_resolved`/`symptom_suppressed`
counts (the [Fake Fix Detector](/guardrails/)'s two possible verified outcomes), `citation_coverage`
(fraction of runs whose [Diagnosis](/agents/diagnosis-agent.md) step produced at least one cited
hypothesis — always checked, since Diagnosis runs before any policy-gate short-circuit), and
`cache_checks`/`cache_hits` (from `SpecialistResult.cache_hit` on the Diagnosis/Planner trace
entries — confirms [the model-call cache](/architecture/model-call-cache.md) is actually working on a replay, not
just present in code). Also carries a `voice_fixtures` status string, currently reporting the real
voice-sample gap (0 of the required ≥2 — see [Voice Intake](/intake/voice-intake.md)) rather than
omitting it.[^harness-py]

`main.py`'s `GET /metrics/summary` reads this file for its `scenario_eval_status` field instead of
computing anything live — a manually-run report, not a per-request computation.

# Verified

Two consecutive full runs (2026-08-17): 14/14 scenarios passed both times, no flakiness. 18/28
cache checks hit on the second (replay) pass — see [Model-Call Cache](/architecture/model-call-cache.md) for why
not 28/28.

[^harness-py]: backend/eval/harness.py
