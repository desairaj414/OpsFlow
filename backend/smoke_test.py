"""Standalone smoke test — run the moment the event API key is issued.

    python smoke_test.py           # fast: HANDBOOK_MODELS only (~4 calls) + the 3 blocking checks
    python smoke_test.py --full    # slow: every model in MODELS (~32 calls) — only for a full re-audit

What it does:
  1. Pre-caches the tiktoken encoding locally (no network needed after this).
  2. Sends ONE minimal chat request to each model in the active set (default:
     HANDBOOK_MODELS — the PRD only requires these 4 chat models explicitly;
     --full sweeps every model in MODELS instead, for a periodic full audit).
  3. Prints a clear PASS/FAIL table.
  4. Shells out to `ollama list` and prints installed local models.
  5. Runs the 3 explicit blocking checks: Whisper, Llama Vision, embedding->Chroma round-trip.

NEVER pulls/downloads a model — lab laptops come pre-installed.
"""
# MUST be first — before any tiktoken/langchain import.
import os
os.environ["TIKTOKEN_CACHE_DIR"] = "./token"

# Corporate proxy MITM certs break tiktoken's internal downloader (uses `requests`) too — bypass globally.
import ssl
import requests
import urllib3

ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_orig_request = requests.Session.request


def _unverified_request(self, *args, **kwargs):
    kwargs["verify"] = False
    return _orig_request(self, *args, **kwargs)


requests.Session.request = _unverified_request

import base64
import io
import math
import struct
import subprocess
import sys
import time
import wave

import httpx
import tiktoken
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://genailab.tcs.in/v1").rstrip("/")
API_KEY = os.getenv("API_KEY", "")
MODELS = [m.strip() for m in os.getenv("MODELS", "").split(",") if m.strip()]
HANDBOOK_MODELS = [m.strip() for m in os.getenv("HANDBOOK_MODELS", "").split(",") if m.strip()]
FULL_SWEEP = "--full" in sys.argv
ACTIVE_MODELS = MODELS if FULL_SWEEP else (HANDBOOK_MODELS or MODELS)


def precache_tiktoken() -> None:
    print("\n=== Pre-caching tiktoken encoding ===")
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        enc.encode("warmup")
        print(f"OK — cached under {os.environ['TIKTOKEN_CACHE_DIR']}")
    except Exception as exc:  # pragma: no cover
        print(f"FAILED to cache tiktoken encoding: {exc}")


def test_model(client: httpx.Client, model: str) -> tuple[str, str]:
    """Send one minimal real request to `model`. Returns (status, detail) — detail
    includes latency and token usage where the gateway reports them (PRD Phase 0 step 4)."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
    }
    start = time.perf_counter()
    try:
        resp = client.post(
            f"{BASE_URL}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=30,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        if resp.status_code == 200:
            usage = resp.json().get("usage", {})
            return "PASS", f"200 OK, {elapsed_ms:.0f}ms, tokens={usage}"
        return "FAIL", f"HTTP {resp.status_code} ({elapsed_ms:.0f}ms): {resp.text[:150]}"
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return "FAIL", f"({elapsed_ms:.0f}ms) {str(exc)[:150]}"


def _generate_test_wav() -> bytes:
    """0.5s of a 440Hz tone, 16kHz mono 16-bit — a real (non-silent) audio payload
    generated locally so the Whisper check needs no external sample file."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        frames = bytearray()
        for i in range(8000):
            val = int(3000 * math.sin(2 * math.pi * 440 * (i / 16000)))
            frames += struct.pack("<h", val)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def _generate_test_png(width: int = 64, height: int = 64, rgb: tuple[int, int, int] = (220, 20, 20)) -> bytes:
    """Solid-color PNG built from stdlib only (zlib/struct/base64) — a 1x1 pixel gets rejected
    by several providers as 'unsupported image', so this needs to be a real minimum-size image."""
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    idat = zlib.compress(raw, 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


_TEST_PNG_B64 = base64.b64encode(_generate_test_png()).decode()

# Llama Vision (azure_ai/genailab-maas-Llama-3.2-90B-Vision-Instruct) is confirmed permanently
# unreachable (HTTP 404/410 DeploymentNotFound/deprecated, re-checked 2026-08-07). Human-approved
# substitute: gpt-4o (already DEFAULT_CHAT_MODEL, fastest + most accurate of the candidates tested).
# See models-routing.md "CONFIRMED UNREACHABLE" and decisions-log.md for the full record.
VISION_MODEL = os.getenv("VISION_MODEL_SUBSTITUTE", "genailab-maas-gpt-4o")


def test_whisper(client: httpx.Client) -> tuple[str, str]:
    """PRD Phase 0 step 2 (BLOCKING): confirm Whisper explicitly via the real
    audio/transcriptions endpoint — the generic chat sweep can't exercise this."""
    whisper_model = next((m for m in MODELS if "whisper" in m.lower()), None)
    if not whisper_model:
        return "FAIL", "no whisper model found in MODELS (.env)"
    start = time.perf_counter()
    try:
        resp = client.post(
            f"{BASE_URL}/audio/transcriptions",
            files={"file": ("test.wav", _generate_test_wav(), "audio/wav")},
            data={"model": whisper_model},
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=30,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        if resp.status_code == 200:
            text = resp.json().get("text", "")
            return "PASS", f"{whisper_model}, {elapsed_ms:.0f}ms, transcript={text!r}"
        return "FAIL", f"{whisper_model} HTTP {resp.status_code} ({elapsed_ms:.0f}ms): {resp.text[:150]}"
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return "FAIL", f"{whisper_model} ({elapsed_ms:.0f}ms) {str(exc)[:150]}"


def test_llama_vision(client: httpx.Client) -> tuple[str, str]:
    """PRD Phase 0 step 2 (BLOCKING): confirm the vision path explicitly by sending an
    actual image_url payload — a plain 'ping' chat call wouldn't exercise vision input.
    Uses VISION_MODEL (gpt-4o substitute), not the deprecated Llama Vision deployment."""
    vision_model = VISION_MODEL
    payload = {
        "model": vision_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Reply with one word: what color is this image?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{_TEST_PNG_B64}"}},
                ],
            }
        ],
        "max_tokens": 10,
    }
    start = time.perf_counter()
    try:
        resp = client.post(
            f"{BASE_URL}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=30,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            return "PASS", f"{vision_model}, {elapsed_ms:.0f}ms, reply={content[:60]!r}"
        return "FAIL", f"{vision_model} HTTP {resp.status_code} ({elapsed_ms:.0f}ms): {resp.text[:150]}"
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return "FAIL", f"{vision_model} ({elapsed_ms:.0f}ms) {str(exc)[:150]}"


def test_embedding_chroma_roundtrip(client: httpx.Client) -> tuple[str, str]:
    """PRD Phase 0 step 5 (BLOCKING): embed one string via the gateway, store it in an
    ephemeral in-memory Chroma collection, query it back, confirm the round-trip matches."""
    embed_model = os.getenv("DEFAULT_EMBED_MODEL", "")
    if not embed_model:
        return "FAIL", "DEFAULT_EMBED_MODEL not set in .env"
    text = "Phase 0 embedding round-trip smoke test string."
    start = time.perf_counter()
    try:
        resp = client.post(
            f"{BASE_URL}/embeddings",
            json={"model": embed_model, "input": text},
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=30,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        if resp.status_code != 200:
            return "FAIL", f"embed call HTTP {resp.status_code} ({elapsed_ms:.0f}ms): {resp.text[:150]}"
        vector = resp.json()["data"][0]["embedding"]
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return "FAIL", f"embed call ({elapsed_ms:.0f}ms) {str(exc)[:150]}"

    try:
        import chromadb

        chroma_client = chromadb.EphemeralClient()
        coll = chroma_client.get_or_create_collection("phase0_roundtrip")
        coll.add(ids=["p0-1"], embeddings=[vector], documents=[text])
        result = coll.query(query_embeddings=[vector], n_results=1)
        if result["documents"] and result["documents"][0] and result["documents"][0][0] == text:
            return "PASS", f"{embed_model}, dim={len(vector)}, {elapsed_ms:.0f}ms, round-trip matched"
        return "FAIL", f"round-trip mismatch: {result}"
    except ImportError:
        return "FAIL", "chromadb not installed — run: pip install -r requirements.txt"
    except Exception as exc:
        return "FAIL", f"chroma error: {str(exc)[:150]}"


def run_model_smoke_tests() -> list[tuple[str, str, str]]:
    label = "MODELS (--full)" if FULL_SWEEP else "HANDBOOK_MODELS (default — pass --full for all)"
    print(f"\n=== Testing {len(ACTIVE_MODELS)} model(s) from {label} ===")
    if not ACTIVE_MODELS:
        print("No models configured — nothing to test.")
        return []

    results = []
    # verify=False: corporate network SSL bypass (self-signed / MITM proxy certs).
    with httpx.Client(verify=False) as client:
        for model in ACTIVE_MODELS:
            status, detail = test_model(client, model)
            results.append((model, status, detail))
            time.sleep(0.2)
    return results


def print_results_table(results: list[tuple[str, str, str]]) -> None:
    if not results:
        return
    name_w = max(len(m) for m, _, _ in results) + 2
    print("\n" + "-" * (name_w + 60))
    print(f"{'MODEL'.ljust(name_w)}{'STATUS'.ljust(8)}DETAIL")
    print("-" * (name_w + 60))
    for model, status, detail in results:
        print(f"{model.ljust(name_w)}{status.ljust(8)}{detail}")
    print("-" * (name_w + 60))
    passed = sum(1 for _, s, _ in results if s == "PASS")
    print(f"{passed}/{len(results)} models PASSED\n")


def list_ollama_models() -> None:
    print("=== Local ollama models (ollama list) ===")
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            print(result.stdout or "(no output)")
        else:
            print(f"`ollama list` exited {result.returncode}: {result.stderr}")
    except FileNotFoundError:
        print("ollama CLI not found on PATH — skipping.")
    except Exception as exc:
        print(f"Could not run `ollama list`: {exc}")


if __name__ == "__main__":
    precache_tiktoken()
    results = run_model_smoke_tests()
    print_results_table(results)
    list_ollama_models()

    print("\n=== Phase 0 BLOCKING checks (explicit, correct call shape per model type) ===")
    with httpx.Client(verify=False) as client:
        blocking_checks = [
            ("Whisper (audio/transcriptions)", *test_whisper(client)),
            ("Llama Vision (chat + image_url)", *test_llama_vision(client)),
            ("Embedding -> Chroma round-trip", *test_embedding_chroma_roundtrip(client)),
        ]
    for name, status, detail in blocking_checks:
        print(f"{status:6} {name}: {detail}")

    any_general_fail = bool(results) and any(s == "FAIL" for _, s, _ in results)
    any_blocking_fail = any(status == "FAIL" for _, status, _ in blocking_checks)
    if any_general_fail or any_blocking_fail:
        sys.exit(1)
