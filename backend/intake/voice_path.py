"""Whisper voice intake path: audio -> transcription -> scrub -> intent parse -> MaintenanceSignal.
domain-privacy.md ordering, not optional: scrubber runs AFTER modality conversion, BEFORE anything
else touches the text (including the intent parser). Confirmation-before-action for side-effecting
intents is enforced by MaintenanceSignal.requires_human_confirmation — this module only sets that
flag, the actual on-screen confirmation UI is Phase 4.
"""
import uuid
from datetime import datetime, timezone

import config  # noqa: F401  sets TIKTOKEN_CACHE_DIR + SSL bypass as a side effect
import httpx

from guardrails.scrubber import scrub
from intake.voice_intent import INTENT_UNRECOGNIZED, parse_voice_intent
from orchestrator.contracts import MaintenanceSignal

_http_client = httpx.Client(verify=False)


def _transcribe(audio_bytes: bytes, filename: str = "voice.wav") -> str:
    resp = _http_client.post(
        f"{config.BASE_URL}/audio/transcriptions",
        files={"file": (filename, audio_bytes, "audio/wav")},
        data={"model": "azure/genailab-maas-whisper"},
        headers={"Authorization": f"Bearer {config.API_KEY}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("text", "")


def run_voice_intake(audio_bytes: bytes, filename: str = "voice.wav") -> MaintenanceSignal:
    # filename matters: Whisper infers audio format from the extension, and a real browser
    # MediaRecorder upload is WebM/Opus, not WAV — mislabeling it as .wav breaks transcription.
    raw_transcript = _transcribe(audio_bytes, filename=filename)

    scrub_result = scrub(raw_transcript, use_slm=True)  # scrub BEFORE intent parsing, per domain-privacy.md
    parsed = parse_voice_intent(scrub_result.scrubbed_text)

    candidate_ci_refs = [parsed.params["ci_id"]] if "ci_id" in parsed.params else []
    candidate_incident_refs = [parsed.params["target_id"]] if "target_id" in parsed.params else []

    return MaintenanceSignal(
        signal_id=f"SIG-{uuid.uuid4().hex[:8]}",
        modality="voice",
        received_at=datetime.now(timezone.utc).isoformat(),
        raw_ref=None,  # raw audio never persisted beyond the run, per domain-privacy.md
        extracted_text=scrub_result.scrubbed_text,
        candidate_ci_refs=candidate_ci_refs,
        candidate_alert_refs=candidate_incident_refs,  # incident/ticket target from voice, not an alert per se
        confidence=1.0 if parsed.intent != INTENT_UNRECOGNIZED else 0.0,
        requires_human_confirmation=parsed.requires_human_confirmation or parsed.intent == INTENT_UNRECOGNIZED,
        parsed_intent=parsed.intent,
    )
