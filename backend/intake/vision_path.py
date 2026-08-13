"""Vision image intake path: image -> extraction -> scrub -> MaintenanceSignal, cited thereafter
as IMG-nnn so provenance survives into diagnosis (domain-multimodal-intake.md). Confirmation-
before-action is unconditional here: every image signal requires human confirmation before
entering a workflow.

Extraction is bound to whichever provider is active on the current request (provider_context.py)
— every provider in the registry supports vision (providers.py), unlike voice transcription.
"""
import base64
import json
import re
import uuid
from datetime import datetime, timezone

import config  # noqa: F401  sets TIKTOKEN_CACHE_DIR + TCS_NETWORK-gated SSL bypass as a side effect
import httpx

import providers
from guardrails.scrubber import scrub
from orchestrator.contracts import MaintenanceSignal
from provider_context import get_active_api_key, get_active_provider

_CI_REF_PATTERN = re.compile(r"\bCI-\d{4,}\b")
_verified_client = httpx.Client(verify=True)
_unverified_client = httpx.Client(verify=False)

_EXTRACTION_PROMPT = (
    "You are analyzing a screenshot for an IT incident (error dialog, stack trace, or monitoring "
    "chart). Extract: any error message text, any identifiers (CI IDs like CI-0001, hostnames, "
    "service names), and any visible timestamps. Respond with ONLY valid JSON (no markdown "
    'fences): {"error_text": "...", "identifiers": ["..."], "timestamps": ["..."]}'
)


def _extract(image_b64: str, mime_type: str = "image/png") -> dict:
    provider_name = get_active_provider()
    provider_cfg = providers.PROVIDERS[provider_name]
    http_client = _unverified_client if provider_cfg["needs_ssl_bypass"] else _verified_client
    resp = http_client.post(
        f"{provider_cfg['base_url'].rstrip('/')}/chat/completions",
        json={
            "model": provider_cfg["roles"]["vision"],
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": _EXTRACTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
                ],
            }],
            "max_tokens": 300,
        },
        headers={"Authorization": f"Bearer {providers.api_key_for(provider_name, get_active_api_key())}"},
        timeout=45,  # live-tested 2026-08-11: Gemini vision can take close to 30s under load
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
