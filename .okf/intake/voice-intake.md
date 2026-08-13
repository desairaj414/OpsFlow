---
type: Module
title: Voice Intake
description: Audio -> Whisper (or provider-equivalent) transcription -> scrub -> a deterministic closed-vocabulary intent parser -> MaintenanceSignal. Scoped to 6 audited commands, never free-form dictation.
resource: backend/intake/voice_path.py
tags: [intake, voice, multimodal]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: voice-path-py
    resource: backend/intake/voice_path.py
    title: backend/intake/voice_path.py
    last_modified: 2026-08-11
  - id: voice-intent-py
    resource: backend/intake/voice_intent.py
    title: backend/intake/voice_intent.py
    last_modified: 2026-08-07
  - id: domain-multimodal
    resource: .knowledge/domain-multimodal-intake.md
    title: Domain — Multimodal Intake
    last_modified: 2026-08-07
---

# Overview

`run_voice_intake(audio_bytes, filename)` transcribes audio via the active provider's transcription
endpoint (only providers with `supports_transcription: True` in the
[Provider Registry](/architecture/provider-registry.md) offer this — currently only `tcs`; the
frontend hides the voice-intake UI for others, and the backend raises a clear error too, as defense
in depth), then — critically — **scrubs the transcript before intent parsing**, per the
scrub-after-convert, scrub-before-anything-else ordering.[^voice-path-py]

# Closed-vocabulary intent parsing — deliberately not an LLM

`parse_voice_intent()` (`backend/intake/voice_intent.py`) matches only 6 audited intents by regex:
`show_open_incidents`, `show_incident <id>`, `approve <id>`, `reject <id> with reason <text>`,
`what_changed_on_ci <id>`, `start_scenario <name>`. Anything that doesn't match is
`unrecognized` and flagged for human confirmation — never a silently-guessed best match. This list
is not to be expanded without explicit human sign-off; it is a deliberate, audited scope,
not an incomplete feature.[^voice-intent-py] See
[Model Routing](/architecture/model-routing.md) — the decisive reason is safety, not cost: a
misheard command reaching an approval action is unacceptable, so command-scope plus on-screen
confirmation is the chosen safety mechanism rather than smarter NLU.

# Confirmation-before-action

`approve_x`, `reject_x`, and `start_scenario` require on-screen confirmation before executing
(`requires_human_confirmation`); read-only queries don't. Every voice action lands in the audit log
tagged `modality: voice`.[^voice-intent-py]

# What's real vs. recognized-but-unwired

As of this bundle's writing, `approve_x`/`reject_x` are wired to a real action (the audited
`/workflows/decision` path). The other 4 intents are recognized and displayed on screen but not
wired to an action — no incidents-list/scenario-library endpoint exists yet for them to act
against; this is stated honestly in the UI rather than faked.

# Consumers

The Sidebar's push-to-talk mic and the [Chat Widget](/architecture/cockpit-ui.md)'s mic button both
go through this same path — one pipeline, not two parsers.

[^voice-path-py]: backend/intake/voice_path.py
[^voice-intent-py]: backend/intake/voice_intent.py
