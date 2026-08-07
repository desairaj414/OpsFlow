"""Tests for the Llama Vision (gpt-4o substitute) image intake path — against a synthetic
error-dialog screenshot with real readable text (a blank/solid-color image wouldn't exercise
extraction at all, see smoke_test.py's vision check for why that needed fixing too)."""
import io

from PIL import Image, ImageDraw

from intake.vision_path import run_vision_intake


def _make_error_screenshot() -> bytes:
    img = Image.new("RGB", (500, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "ERROR: Connection refused", fill=(200, 0, 0))
    draw.text((10, 40), "Service: CI-0087 unreachable", fill=(0, 0, 0))
    draw.text((10, 70), "Timestamp: 2026-08-07 12:00:00", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_vision_intake_extracts_ci_ref_and_requires_confirmation():
    signal = run_vision_intake(_make_error_screenshot())
    assert signal.modality == "image"
    assert signal.signal_id.startswith("IMG-")
    assert signal.raw_ref is None  # raw image never persisted
    assert signal.requires_human_confirmation is True  # unconditional for vision path
    assert "CI-0087" in signal.candidate_ci_refs


def test_vision_intake_scrubs_extracted_text():
    """A screenshot with a visible token should have it redacted before the signal is built."""
    img = Image.new("RGB", (500, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Authorization: Bearer abcdefghijklmnopqrstuvwxyzABCDEFGH", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    signal = run_vision_intake(buf.getvalue())
    assert "abcdefghijklmnopqrstuvwxyzABCDEFGH" not in signal.extracted_text
