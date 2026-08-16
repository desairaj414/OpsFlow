"""scripts/generate_screenshot_fixtures.py
─────────────────────────────────────────
Generates the one committed low-quality/legacy-UI screenshot fixture PRD §6.1 calls for
("Error screenshots ... including one low-quality/legacy-UI capture"). Same synthetic-rendering
technique already used by tests/test_vision_path.py and scripts/pregenerate_demo_outputs.py's
PII demo screenshot — small monospace-only text, no anti-aliasing, downscaled then upscaled to
introduce real compression/blur artifacts, mimicking a legacy terminal/dialog capture rather than
a clean modern dashboard screenshot. Proves the vision-intake bias mitigation (domain-guardrails.md:
"Image-context ... terminal dumps/legacy UIs extract poorly" -> "Extraction confidence surfaced;
mandatory human confirmation") against something that actually IS harder to read, not another clean
image.

    cd backend && python ../scripts/generate_screenshot_fixtures.py
"""
import io
import os

from PIL import Image, ImageDraw

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT_DIR = os.path.join(REPO_ROOT, "data", "screenshots")


def _make_legacy_ui_screenshot() -> bytes:
    # Small canvas, default bitmap font (no anti-aliasing) — closer to a legacy terminal capture
    # than the clean 500x200 white-background dialogs used elsewhere in this repo's fixtures.
    img = Image.new("RGB", (320, 120), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((4, 4), "SYS ALERT 0x4F2", fill=(0, 255, 0))
    draw.text((4, 16), "CI-0121 STATUS=FAULT", fill=(0, 255, 0))
    draw.text((4, 28), "ERRCODE 500 RETRY=3", fill=(0, 255, 0))
    draw.text((4, 40), "TS 2026-08-07T00:00Z", fill=(0, 255, 0))
    # Downscale then upscale with nearest-neighbor to introduce real, non-simulated pixelation/
    # blur — a genuinely lower-fidelity image, not a clean render just labeled "legacy".
    small = img.resize((80, 30), Image.BILINEAR)
    degraded = small.resize((320, 120), Image.NEAREST)
    buf = io.BytesIO()
    degraded.save(buf, format="PNG")
    return buf.getvalue()


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "legacy-ui-001.png")
    with open(path, "wb") as f:
        f.write(_make_legacy_ui_screenshot())
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
