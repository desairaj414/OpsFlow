"""scripts/pregenerate_demo_outputs.py
────────────────────────────────────────
Runs the real agent pipeline once, with a real Free Demo Key (Gemini), against every named
scenario in data/scenarios/SCEN-*.json plus one PII-scrubbing demo fixture, and writes the results
to data/demo_outputs.json. Instant Demo mode (main.py's /workflows/run, /intake/image
short-circuits) reads that file at runtime and never calls a live model.

Mirrors EduCare's scripts/pregenerate_demo_outputs.py: idempotent (a case already in the output
file is skipped, so a partial run — e.g. a rate limit — can just be re-run to finish the rest),
throttled for Gemini's free-tier rate limit, writes after every case so a crash mid-run doesn't
lose progress.

Run this once, locally, with a real key:
    cd backend && GEMINI_API_KEY=... python ../scripts/pregenerate_demo_outputs.py

Scope note: only the image-intake path gets a PII-demo fixture here, not voice — synthesizing
realistic speech audio that actually names a person (so Whisper transcribes something worth
scrubbing) would need a TTS dependency this project doesn't otherwise use. The image path already
proves the same scrubber (guardrails/scrubber.py) end-to-end via a rendered screenshot, same
technique tests/test_vision_path.py already uses for its own fixtures.
"""
import json
import os
import re
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

import config  # noqa: E402  sets TIKTOKEN_CACHE_DIR + TCS_NETWORK-gated SSL bypass as a side effect
import providers  # noqa: E402
from provider_context import set_provider_for_script  # noqa: E402

PREGEN_PROVIDER = os.getenv("PREGEN_PROVIDER", providers.DEMO_PROVIDER)
if not providers.api_key_for(PREGEN_PROVIDER, None):
    raise SystemExit(
        f"No API key configured for provider {PREGEN_PROVIDER!r}. Set GEMINI_API_KEY (or "
        f"OPENROUTER_API_KEY / API_KEY, matching PREGEN_PROVIDER) in backend/.env before running this."
    )
set_provider_for_script(PREGEN_PROVIDER)

import asyncio  # noqa: E402
import io  # noqa: E402

from PIL import Image, ImageDraw  # noqa: E402

from correlation.cluster import _load_alerts, _load_cis_and_relationships  # noqa: E402
from intake.vision_path import run_vision_intake  # noqa: E402
from main import _format_workflow_outcome  # noqa: E402  (safe: only defines the FastAPI app object, no server start)
from orchestrator.mcp_wiring import wire_all_in_process  # noqa: E402
from orchestrator.supervisor import run_workflow  # noqa: E402

DATA_DIR = os.path.join(REPO_ROOT, "data")
SCENARIOS_DIR = os.path.join(DATA_DIR, "scenarios")
OUT_PATH = os.path.join(DATA_DIR, "demo_outputs.json")

# Gemini's free tier caps requests/minute — space calls out and retry with backoff on the rare
# overshoot, same shape as EduCare's script.
MIN_CALL_INTERVAL = 8.0
MAX_RETRIES = 5
_last_call_at = [0.0]


def _throttle() -> None:
    wait = MIN_CALL_INTERVAL - (time.monotonic() - _last_call_at[0])
    if wait > 0:
        time.sleep(wait)


async def _throttled_run_workflow(**kwargs) -> dict:
    for attempt in range(1, MAX_RETRIES + 1):
        _throttle()
        try:
            result = await run_workflow(**kwargs)
            _last_call_at[0] = time.monotonic()
            return result
        except Exception as e:
            msg = str(e)
            if "429" not in msg and "RESOURCE_EXHAUSTED" not in msg and "rate" not in msg.lower():
                raise
            m = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+)", msg)
            delay = float(m.group(1)) + 2 if m else 30.0
            print(f"  rate limited (attempt {attempt}/{MAX_RETRIES}), waiting {delay:.0f}s...")
            time.sleep(delay)
    raise RuntimeError(f"Gave up after {MAX_RETRIES} rate-limit retries")


def _load_scenarios() -> list[dict]:
    scenarios = []
    for name in sorted(os.listdir(SCENARIOS_DIR)):
        if not name.startswith("SCEN-") or not name.endswith(".json"):
            continue
        with open(os.path.join(SCENARIOS_DIR, name), encoding="utf-8") as f:
            scenarios.append(json.load(f))
    return scenarios


def _make_pii_demo_screenshot() -> bytes:
    """A rendered error dialog naming a person and an email — same PII shapes pii_seed.py plants
    (person_name + email), same rendering technique tests/test_vision_path.py's own fixtures use.
    Run through the real, unmodified run_vision_intake -> scrubber pipeline (domain-privacy.md
    ordering), so the captured MaintenanceSignal shows a genuine [NAME_1]/[EMAIL_1] redaction, not
    a hand-written example."""
    img = Image.new("RGB", (640, 220), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "ERROR: Escalation required", fill=(200, 0, 0))
    draw.text((10, 45), "Service: CI-0059 degraded", fill=(0, 0, 0))
    draw.text((10, 80), "Reported by: Priya Sharma", fill=(0, 0, 0))
    draw.text((10, 110), "Contact: priya.sharma@opsflow-demo.example", fill=(0, 0, 0))
    draw.text((10, 140), "Timestamp: 2026-08-11 09:15:00", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def main() -> None:
    wire_all_in_process()
    cis, _relationships = _load_cis_and_relationships()
    alerts = _load_alerts()
    scenarios = _load_scenarios()

    try:
        with open(OUT_PATH, encoding="utf-8") as f:
            results: dict = json.load(f)
    except FileNotFoundError:
        results = {}

    for scenario in scenarios:
        key = f"{scenario['ci_id']}:{scenario['workflow_type']}"
        if key in results:
            print(f"skip {scenario['id']} ({key}) — already done")
            continue

        print(f"generating {scenario['id']} — {scenario['name']}")
        ci = next((c for c in cis if c["id"] == scenario["ci_id"]), None)
        if ci is None:
            raise SystemExit(f"{scenario['id']}: CI {scenario['ci_id']} not found in CMDB — data drifted?")
        scenario_alerts = [
            a for a in alerts if a["ci_id"] == scenario["ci_id"] and a["category"] == scenario.get("alert_category", "fault")
        ]
        incident_id = f"INC-DEMO-{scenario['id']}"

        outcome = await _throttled_run_workflow(
            incident_id=incident_id, ci=ci, alerts=scenario_alerts,
            workflow_type=scenario["workflow_type"], actor_role="operator",
            auto_approve=scenario.get("auto_approve", False),
        )
        formatted = await _format_workflow_outcome(
            incident_id, outcome, modality="alert", workflow_type=scenario["workflow_type"],
        )
        results[key] = formatted
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    if "image_pii_demo" not in results:
        print("generating image_pii_demo (PII-scrubbing showcase, vision intake)")
        # Gemini's vision model returned genuine "high demand, try again later" 503s + read
        # timeouts during this build (confirmed via the API's own error message, not a quota or
        # code issue) — retry with backoff rather than treating a transient outage as fatal.
        screenshot = _make_pii_demo_screenshot()
        for attempt in range(5):
            try:
                signal = run_vision_intake(screenshot)
                break
            except Exception as e:
                if attempt == 4:
                    raise
                print(f"  vision call failed ({e}), retrying in 20s (attempt {attempt + 1}/5)...")
                time.sleep(20)
        results["image_pii_demo"] = signal.model_dump()
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    else:
        print("skip image_pii_demo — already done")

    print(f"\nDone. {len(results)} entries in {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
