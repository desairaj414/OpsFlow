# Voice samples — synthetic placeholders in place, real recordings still wanted

PRD §6.1/§6.3 require **≥2 deliberately noisy or accented voice-command samples**, and are explicit
that these must be **real, recorded, consented human speech** ("recorded by team members, who
consent, and who are the only people audible") — not synthetic/TTS-generated audio. This project's
AI assistant genuinely cannot record real speech, so on 2026-08-17, with the human's explicit
approval, it generated **synthetic placeholders instead** (Windows SAPI text-to-speech) so the
pipeline has something to exercise now — these are clearly labeled as synthetic everywhere they're
referenced (this file, `citations.md`, the eval harness's report) and are not claimed to satisfy
PRD §6.3's real-recording requirement. Replace them with real recordings whenever that's possible.

## What's here (synthetic, generated via `Add-Type -AssemblyName System.Speech`)
- `accented_approve_command.wav` — "Approve INC-0042", Microsoft Ravi (en-IN) voice. Closed-vocabulary command.
- `accented_names_colleague.wav` — "Please let Priya Sharma know the incident is resolved", Microsoft Heera (en-IN) voice. Free-form (not closed-vocabulary — should parse as `unrecognized`/needs confirmation), names a colleague per PRD §6.2's scrubber-exercise requirement.
- `noisy_show_open_incidents.wav` — "Show open incidents", Microsoft Zira voice, then mixed with synthetic white noise (±1800 amplitude on 16-bit PCM, pure-Python `wave`/`struct`, no new dependency) to genuinely degrade the signal, not just relabel a clean recording.

## Known limitation
Synthetic TTS speech doesn't reproduce the actual acoustic/coarticulation patterns of a real
accented or noisy human recording — it's useful for exercising the transcribe→scrub→parse pipeline
end to end (does the code path work at all, does scrubbing still fire on transcribed text, is an
unrecognized command correctly flagged for confirmation), not for validating real-world ASR
accuracy/bias claims. The bias-mitigation claim in `domain-guardrails.md`'s table ("Accent/
speech-pattern... command-scoped closed vocabulary... parsed intent shown for confirmation") is
about the *system's design response* to imperfect recognition, which these fixtures do exercise;
it is not a claim that these specific files prove ASR fairness across real accents.

## What's needed for the real thing
- **≥2 `.wav`/`.mp3` files** of real speech, each a short push-to-talk command from the closed
  vocabulary (`intake/voice_intent.py`), spoken with real background noise or a non-neutral accent.
- Save them here as `data/voice_samples/*.wav` — the eval harness (`backend/eval/harness.py`,
  `_check_voice_fixtures()`) already picks up every `.wav` in this directory automatically, no code
  change needed, and will report on whichever files are actually here.
- Once real recordings exist, delete or clearly separate the synthetic ones so a future reader
  doesn't mistake one for the other.
