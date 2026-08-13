---
type: Module
title: Pregenerate Script
description: Runs the real agent pipeline once, with a real Free Demo Key, against every named scenario plus one PII-scrubbing demo fixture, and writes the results to data/demo_outputs.json for Instant Demo mode to replay with zero live calls.
resource: scripts/pregenerate_demo_outputs.py
tags: [demo, tooling]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: pregenerate-py
    resource: scripts/pregenerate_demo_outputs.py
    title: scripts/pregenerate_demo_outputs.py
    last_modified: 2026-08-11
---

# Overview

Run once, locally, with a real key: `cd backend && GEMINI_API_KEY=... python
../scripts/pregenerate_demo_outputs.py`. It wires the same in-process MCP/A2A stack the live app
uses (`orchestrator/mcp_wiring.py`), loads every `data/scenarios/SCEN-*.json` fixture, and for each
one runs the real `run_workflow()` — the identical Supervisor path a live visitor's click would
trigger — then formats and writes the result to `data/demo_outputs.json`, keyed by
`f"{ci_id}:{workflow_type}"`.[^pregenerate-py]

# Idempotent and crash-safe

A scenario key already present in the output file is skipped, so a partial run (e.g. hitting a rate
limit) can simply be re-run to finish the rest. The output file is rewritten after **every** case,
not just at the end, so a crash mid-run doesn't lose already-generated progress.[^pregenerate-py]

# Rate-limit handling

`MIN_CALL_INTERVAL = 8.0` throttles calls to stay under Gemini's free-tier requests-per-minute cap;
on a 429/`RESOURCE_EXHAUSTED` response it parses the provider's own suggested `retryDelay` out of
the error message and retries (up to 5 attempts) rather than failing the whole run over a transient
rate limit.[^pregenerate-py]

# PII-demo fixture

Beyond the named scenarios, the script also generates one `image_pii_demo` entry: a rendered error
dialog naming a person and an email address, run through the real, unmodified
[Vision Intake](/intake/vision-intake.md) pipeline, so the captured `MaintenanceSignal` shows a
genuine `[NAME_1]`/`[EMAIL_1]` redaction rather than a hand-written example. Only the image path
gets this treatment — synthesizing realistic speech audio naming a person would need a
text-to-speech dependency the project doesn't otherwise use.[^pregenerate-py]

[^pregenerate-py]: scripts/pregenerate_demo_outputs.py
