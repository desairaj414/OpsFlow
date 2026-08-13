---
type: Module
title: Vision Intake
description: Screenshot/error-image -> vision-model extraction -> scrub -> MaintenanceSignal, cited thereafter as IMG-nnn so provenance survives into diagnosis. Human confirmation is unconditional for every image signal.
resource: backend/intake/vision_path.py
tags: [intake, vision, multimodal]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: vision-path-py
    resource: backend/intake/vision_path.py
    title: backend/intake/vision_path.py
    last_modified: 2026-08-11
  - id: domain-multimodal
    resource: .knowledge/domain-multimodal-intake.md
    title: Domain — Multimodal Intake
    last_modified: 2026-08-07
---

# Overview

`run_vision_intake(image_bytes, mime_type)` sends the image plus an extraction prompt to the active
provider's `vision`-role model (see [Provider Registry](/architecture/provider-registry.md) — every
registered provider supports vision, unlike voice transcription), asking for error text,
identifiers, and timestamps as JSON. The combined extracted text is then scrubbed before anything
else touches it, and CI references (`CI-\d{4,}` pattern) are parsed from the **scrubbed** text so a
redaction can never accidentally remove or corrupt a real CI id used downstream.[^vision-path-py]

# Unconditional confirmation

Unlike voice (where only side-effecting intents require confirmation), every image signal sets
`requires_human_confirmation=True` unconditionally — extraction confidence from a screenshot is
treated as inherently less trustworthy than a matched voice command, per
[Bias Mitigation](/guardrails/bias-mitigation.md)'s image-context row (modern dashboards extract
cleanly; terminal dumps and legacy UIs extract poorly).[^vision-path-py]

# Consumers

`orchestrator/intake_adapter.py`'s `start_workflow_from_confirmed_signal()` bridges a *confirmed*
signal into a real [Supervisor](/agents/supervisor.md) run — it enforces
`requires_human_confirmation is False` in code before proceeding, not just as a UI convention; a
signal with no resolvable `candidate_ci_refs` is also rejected. The [Chat Widget](/architecture/cockpit-ui.md)'s
image-upload button is the current UI entry point for this path.

[^vision-path-py]: backend/intake/vision_path.py
