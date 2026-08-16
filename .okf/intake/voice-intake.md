---
type: Module
title: Voice Intake
description: Audio -> Whisper (or provider-equivalent) transcription -> scrub -> a deterministic closed-vocabulary intent parser -> MaintenanceSignal. Scoped to 6 audited commands, never free-form dictation.
resource: backend/intake/voice_path.py
tags: [intake, voice, multimodal]
status: stable
generated: { by: "claude-sonnet-5/okf-maintain", at: "2026-08-16T00:00:00Z" }
sources:
  - id: voice-path-py
    resource: backend/intake/voice_path.py
    title: backend/intake/voice_path.py
    last_modified: 2026-08-13
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
[Provider Registry](/architecture/provider-registry.md) offer this — currently `tcs` (Whisper) and
`openai` (`whisper-1`); Gemini/OpenRouter/Grok don't, and this is a fixed fact of each provider's
API surface, not something that changes with a paid account — Gemini's OpenAI-compat layer has
never exposed `/audio/transcriptions`, free or paid. `custom` is the one exception: since an
arbitrary endpoint's support is genuinely unknown ahead of time, `providers.py`'s
`probe_transcription_support()` actually checks for a working `/audio/transcriptions` route at
login (404 vs. not) rather than guessing, and the frontend trusts that real result over its static
default. The frontend hides the voice-intake UI for providers/endpoints that don't support it
(`canUseVoice()`, `frontend/src/lib/providers.js`), and the backend raises a clear error too, as
defense in depth), then — critically — **scrubs the transcript before intent
parsing**, per the scrub-after-convert, scrub-before-anything-else ordering.[^voice-path-py] The
returned `MaintenanceSignal` also carries `slm_pass_ran` (see [Scrubber](/guardrails/scrubber.md))
so the chat UI can warn if the local name-scrubbing model wasn't reachable for this transcript.

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

# Confirmation-before-action (as designed; superseded downstream, see Consumers)

By design, `parse_voice_intent()`'s own output marks `approve_x`, `reject_x`, and `start_scenario`
as needing on-screen confirmation before executing (`requires_human_confirmation`); read-only
queries don't. This field still computes and still lands on the returned `MaintenanceSignal`, but
see Consumers below for what actually acts on a transcript today.

# What's real vs. recognized-but-unwired — corrected, this section was stale

Earlier revisions of this file said `approve_x`/`reject_x` were "wired to a real action" and the
other 4 intents were "recognized and displayed on screen." That's no longer how the live path
works. `ChatWidget.jsx`'s `transcribeAndSend()` reads only `signal.extracted_text` and
`signal.slm_pass_ran` off the `/intake/voice` response — `signal.parsed_intent` is never read
anywhere in the frontend. The scrubbed transcript is forwarded as an ordinary text message into
`/chat`, which runs its own separate LLM-based intent classifier
(`query_tickets`/`approve_incident`/`reject_incident`/`app_help`/`unrecognized` — see
[Cockpit UI](/architecture/cockpit-ui.md)'s Floating chat assistant section) — a different
vocabulary and mechanism from `voice_intent.py`'s regex parser. `parse_voice_intent()` still runs
server-side on every voice signal and its result is still attached to the `MaintenanceSignal`, but
nothing currently displays or acts on it — it's dead data as of this correction, not a documentation
error about what the code does.

# Consumers

The [Chat Widget](/architecture/cockpit-ui.md)'s mic button is the only voice-input surface — a
Sidebar push-to-talk button existed early on but was consolidated into the Chat Widget by explicit
request (one conversational surface instead of two). The transcript itself flows through one
pipeline (Whisper/provider-equivalent → scrub → `/chat`'s own intent classifier); `voice_intent.py`'s
closed-vocabulary parse is a second, currently-unconsumed classification of the same transcript —
see the corrected section above.

[^voice-path-py]: backend/intake/voice_path.py
[^voice-intent-py]: backend/intake/voice_intent.py
