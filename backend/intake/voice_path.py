"""Whisper voice intake path: audio -> transcription -> scrub -> intent parse -> MaintenanceSignal.
domain-privacy.md ordering, not optional: scrubber runs AFTER modality conversion, BEFORE anything
else touches the text (including the intent parser). Confirmation-before-action for side-effecting
intents is enforced by MaintenanceSignal.requires_human_confirmation — this module only sets that
flag, the actual on-screen confirmation UI is Phase 4.

Transcription is bound to whichever provider is active on the current request (provider_context.py)
— only providers with `supports_transcription: True` (see providers.py) actually offer a Whisper-
equivalent endpoint; the frontend hides the voice-intake UI for the others (roles.js canUseVoice()),
and `run_voice_intake` raises a clear error here too if it's ever called anyway (defense in depth).
"""
import uuid
from datetime import datetime, timezone

import config  # noqa: F401  sets TIKTOKEN_CACHE_DIR + TCS_NETWORK-gated SSL bypass as a side effect
import httpx

import providers
from guardrails.scrubber import scrub
from intake.voice_intent import INTENT_UNRECOGNIZED, parse_voice_intent
from orchestrator.contracts import MaintenanceSignal
from provider_context import get_active_api_key, get_active_provider

_verified_client = httpx.Client(verify=True)
_unverified_client = httpx.Client(verify=False)


def _transcribe(audio_bytes: bytes, filename: str = "voice.wav") -> str:
    provider_name = get_active_provider()
    provider_cfg = providers.PROVIDERS[provider_name]
    if not provider_cfg["supports_transcription"]:
        raise ValueError(f"{provider_cfg['label']} does not support voice transcription — switch provider.")
    http_client = _unverified_client if provider_cfg["needs_ssl_bypass"] else _verified_client
    resp = http_client.post(
        f"{provider_cfg['base_url'].rstrip('/')}/audio/transcriptions",
        files={"file": (filename, audio_bytes, "audio/wav")},
        data={"model": provider_cfg["whisper_model"]},
        headers={"Authorization": f"Bearer {providers.api_key_for(provider_name, get_active_api_key())}"},
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
