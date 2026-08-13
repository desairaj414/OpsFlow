---
type: Module
title: Scrubber
description: PII/secrets redaction pipeline — a regex pass for structured identifiers/secrets plus a local-only Ollama SLM pass for free-text person names — with reversible tokenisation and a separate prompt-injection flag.
resource: backend/guardrails/scrubber.py
tags: [guardrails, privacy, pii]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: scrubber-py
    resource: backend/guardrails/scrubber.py
    title: backend/guardrails/scrubber.py
    last_modified: 2026-08-11
  - id: domain-privacy
    resource: .knowledge/domain-privacy.md
    title: Domain — Privacy, Scrubbing & Audit
    last_modified: 2026-08-07
---

# Overview

`scrub(text, use_slm=True) -> ScrubResult` runs before any text reaches a hosted model boundary —
after modality conversion (transcription/extraction), before anything else touches it, including
intent parsing.[^domain-privacy] Two passes:

1. **Regex** — structured items in priority order (connection strings and API keys/bearer tokens
   matched before bare IP/email patterns, so a connection string is redacted whole rather than
   partially matched inside): connection strings, API keys, bearer tokens, emails, employee IDs,
   private IPs, internal hostnames, phone numbers.[^scrubber-py]
2. **Local SLM** (Ollama, `llama-3.2-3b-it`, localhost only) — free-text person names regex can't
   reliably catch. "Highest-sensitivity content never leaves the machine" is a privacy
   *architecture* choice here, not a cost optimization.[^domain-privacy] If Ollama is unreachable,
   this pass fails closed (returns the regex-only result, `slm_pass_ran=False`) rather than raising.

# Reversible tokenisation

Each detected item becomes a token like `[HOST_7]` or `[NAME_1]`, mapped in `token_map` back to the
original value. `restore_text()` reconstructs the original for an authorized human viewer only —
never called to reconstruct text sent to a model.[^scrubber-py]

# Prompt-injection flag, not a redaction

A separate `injection_suspected` boolean fires on patterns like "ignore previous instructions" or
"you are now in developer mode." This is a **flag**, not a redaction — containment of an actual
injection attempt is the typed-contract boundary's job downstream (a model's raw output never
short-circuits into an executed action), not something this module claims to solve alone.[^scrubber-py]

# Measured accuracy

Against a 31-item planted ground truth (`data/pii_ground_truth.json`): regex-covered types measured
100% recall (20/20) with zero type confusion; the local-SLM name pass measured 100% recall (10/10)
in the run recorded in `.knowledge/domain-privacy.md` — noted there as inherently probabilistic and
worth re-measuring if the local model changes; the adversarial prompt-injection line was flagged
correctly with zero false positives on clean snippets.[^domain-privacy]

# Consumers

[Voice Intake](/intake/voice-intake.md) and [Vision Intake](/intake/vision-intake.md) both call
`scrub()` immediately after transcription/extraction, before intent parsing or CI-reference
extraction. The core agent chain itself never calls the scrubber — its inputs are synthetic,
already-clean seeded data.

[^scrubber-py]: backend/guardrails/scrubber.py
[^domain-privacy]: Domain — Privacy, Scrubbing & Audit
