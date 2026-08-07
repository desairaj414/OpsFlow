"""Llama Vision image intake path: image -> extraction -> scrub -> MaintenanceSignal, cited
thereafter as IMG-nnn so provenance survives into diagnosis (domain-multimodal-intake.md). Uses
gpt-4o — the human-approved substitute for the permanently-deprecated Llama Vision deployment
(models-routing.md "CONFIRMED UNREACHABLE", decisions-log.md). Confirmation-before-action is
unconditional here: every image signal requires human confirmation before entering a workflow.
"""
import base64
import json
import re
import uuid
from datetime import datetime, timezone

import config  # noqa: F401  sets TIKTOKEN_CACHE_DIR + SSL bypass as a side effect
import httpx

from guardrails.scrubber import scrub
from orchestrator.contracts import MaintenanceSignal

VISION_MODEL = "genailab-maas-gpt-4o"  # Llama Vision substitute, see models-routing.md
_CI_REF_PATTERN = re.compile(r"\bCI-\d{4,}\b")
_http_client = httpx.Client(verify=False)

_EXTRACTION_PROMPT = (
    "You are analyzing a screenshot for an IT incident (error dialog, stack trace, or monitoring "
    "chart). Extract: any error message text, any identifiers (CI IDs like CI-0001, hostnames, "
    "service names), and any visible timestamps. Respond with ONLY valid JSON (no markdown "
    'fences): {"error_text": "...", "identifiers": ["..."], "timestamps": ["..."]}'
)


def _extract(image_b64: str, mime_type: str = "image/png") -> dict:
    resp = _http_client.post(
        f"{config.BASE_URL}/chat/completions",
        json={
            "model": VISION_MODEL,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": _EXTRACTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
                ],
            }],
            "max_tokens": 300,
        },
        headers={"Authorization": f"Bearer {config.API_KEY}"},
        timeout=30,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error_text": content, "identifiers": [], "timestamps": []}


def run_vision_intake(image_bytes: bytes, mime_type: str = "image/png") -> MaintenanceSignal:
    image_b64 = base64.b64encode(image_bytes).decode()
    extracted = _extract(image_b64, mime_type)

    combined_text = extracted.get("error_text", "")
    if extracted.get("identifiers"):
        combined_text += " | identifiers: " + ", ".join(extracted["identifiers"])
    if extracted.get("timestamps"):
        combined_text += " | timestamps: " + ", ".join(extracted["timestamps"])

    scrub_result = scrub(combined_text, use_slm=True)  # scrub BEFORE anything else, per domain-privacy.md
    candidate_ci_refs = sorted(set(_CI_REF_PATTERN.findall(scrub_result.scrubbed_text)))

    return MaintenanceSignal(
        signal_id=f"IMG-{uuid.uuid4().hex[:6]}",
        modality="image",
        received_at=datetime.now(timezone.utc).isoformat(),
        raw_ref=None,  # raw image never persisted beyond the run, per domain-privacy.md
        extracted_text=scrub_result.scrubbed_text,
        candidate_ci_refs=candidate_ci_refs,
        candidate_alert_refs=[],
        confidence=0.7 if combined_text.strip() else 0.0,  # extraction confidence, not a guess of correctness
        requires_human_confirmation=True,  # unconditional for the vision path, per domain-multimodal-intake.md
        parsed_intent=None,  # voice-only field
    )
