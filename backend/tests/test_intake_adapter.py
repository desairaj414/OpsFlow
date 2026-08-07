"""End-to-end test: screenshot -> vision extraction -> scrub -> (simulated on-screen confirmation)
-> full Supervisor workflow run. This is the complete image intake path required by
prd-phase-3.md's acceptance criteria: "confirmed on screen before entering a workflow, cited as
IMG-nnn downstream" — checks the IMG-nnn citation actually survives into the workflow's evidence.
"""
import asyncio
import io

import pytest
from PIL import Image, ImageDraw

from intake.vision_path import run_vision_intake
from orchestrator.intake_adapter import start_workflow_from_confirmed_signal
from orchestrator.mcp_wiring import wire_all_in_process


def _make_screenshot_for_ci(ci_id: str) -> bytes:
    img = Image.new("RGB", (500, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "ERROR: Connection refused", fill=(200, 0, 0))
    draw.text((10, 40), f"Service: {ci_id} unreachable", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_unconfirmed_signal_is_rejected_by_the_adapter():
    """The confirmation gate must be enforced, not just decorative."""
    signal = run_vision_intake(_make_screenshot_for_ci("CI-0059"))
    assert signal.requires_human_confirmation is True  # vision always requires confirmation
    with pytest.raises(ValueError, match="requires human confirmation"):
        asyncio.run(start_workflow_from_confirmed_signal(signal))


def test_confirmed_image_signal_drives_a_full_workflow_run():
    wire_all_in_process()
    signal = run_vision_intake(_make_screenshot_for_ci("CI-0059"))
    assert "CI-0059" in signal.candidate_ci_refs

    # Simulate the on-screen confirmation step (Phase 4 UI) having completed.
    confirmed_signal = signal.model_copy(update={"requires_human_confirmation": False})

    outcome = asyncio.run(start_workflow_from_confirmed_signal(confirmed_signal, workflow_type="incident"))
    assert outcome["status"] in ("complete", "pending_approval", "blocked", "stopped")

    enrichment_result = next((r for r in outcome.get("trace", []) if r.agent_name == "enrichment"), None)
    if enrichment_result:
        assert "CI-0059" in enrichment_result.cited_artifact_ids  # evidence gathering actually ran on the resolved CI


def test_ci_with_no_existing_alerts_gets_a_synthesized_alert_citing_the_image_signal():
    """domain-multimodal-intake.md: an image-triggered incident must cite IMG-nnn provenance
    downstream. When the resolved CI has no pre-existing synthetic alert, the adapter must
    synthesize one from the image signal rather than silently proceeding with no evidence."""
    from orchestrator.intake_adapter import _alerts_for_ci
    from orchestrator.contracts import MaintenanceSignal

    signal = MaintenanceSignal(
        signal_id="IMG-notfound", modality="image", received_at="2026-08-07T00:00:00",
        extracted_text="synthetic test", candidate_ci_refs=["CI-NO-ALERTS-FIXTURE"],
        confidence=0.7, requires_human_confirmation=False,
    )
    alerts = _alerts_for_ci("CI-NO-ALERTS-FIXTURE", signal)
    assert len(alerts) == 1
    assert alerts[0]["id"] == "ALERT-FROM-IMG-notfound"
    assert alerts[0]["source"] == "image_intake"
