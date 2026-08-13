"""Tests for the Whisper voice intake path. No real recorded speech sample is available in this
repo, so this splits into: (1) an integration smoke test that the real Whisper call + full
pipeline don't crash and produce a valid MaintenanceSignal, and (2) unit tests proving the
scrub-then-parse ordering doesn't corrupt intent-critical tokens (the part that matters for
correctness, independent of what a specific audio sample happens to transcribe to).
"""
import pytest

import providers
from guardrails.scrubber import scrub
from intake.voice_intent import INTENT_APPROVE, INTENT_UNRECOGNIZED, parse_voice_intent
from intake.voice_path import run_voice_intake
from smoke_test import _generate_test_wav

_active_provider_supports_transcription = providers.PROVIDERS[providers.DEFAULT_PROVIDER]["supports_transcription"]


@pytest.mark.skipif(
    not _active_provider_supports_transcription,
    reason=f"DEFAULT_PROVIDER={providers.DEFAULT_PROVIDER!r} has no transcription endpoint (providers.py) — "
           "run with DEFAULT_PROVIDER=tcs and a real TCS_NETWORK/API_KEY to exercise this.",
)
def test_voice_intake_produces_valid_signal_against_real_whisper_call():
    signal = run_voice_intake(_generate_test_wav())
    assert signal.modality == "voice"
    assert signal.raw_ref is None  # raw audio never persisted
    assert signal.parsed_intent is not None
    # A generated tone isn't real speech, so recognizing it is not expected — the invariant under
    # test is that unrecognized input is flagged for confirmation, never silently guessed.
    if signal.parsed_intent == INTENT_UNRECOGNIZED:
        assert signal.requires_human_confirmation is True


def test_scrub_then_parse_ordering_preserves_intent_command_structure():
    """A command with an incident ID (not itself PII) must still parse correctly after scrubbing."""
    text = "approve INC-0042"
    scrubbed = scrub(text, use_slm=False).scrubbed_text
    parsed = parse_voice_intent(scrubbed)
    assert parsed.intent == INTENT_APPROVE
    assert parsed.params["target_id"] == "INC-0042"


def test_scrub_then_parse_ordering_redacts_pii_but_keeps_command_recognizable():
    """A more realistic utterance with an embedded email — the email should be gone, but if it
    doesn't match one of the 6 closed-vocabulary shapes, it must be UNRECOGNIZED (never guessed)."""
    text = "please email jane.doe@example.com about this incident"
    scrubbed = scrub(text, use_slm=False).scrubbed_text
    assert "jane.doe@example.com" not in scrubbed
    parsed = parse_voice_intent(scrubbed)
    assert parsed.intent == INTENT_UNRECOGNIZED
    assert parsed.requires_human_confirmation is True
