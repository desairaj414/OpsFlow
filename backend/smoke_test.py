"""Standalone smoke test — run the moment the event API key is issued.

    python smoke_test.py

What it does:
  1. Pre-caches the tiktoken encoding locally (no network needed after this).
  2. Sends ONE minimal chat request to EVERY model listed in MODELS (.env),
     since we won't know which model(s) the PRD needs until later.
  3. Prints a clear PASS/FAIL table.
  4. Shells out to `ollama list` and prints installed local models.

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

import subprocess
import sys
import time

import httpx
import tiktoken
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://genailab.tcs.in/v1").rstrip("/")
API_KEY = os.getenv("API_KEY", "")
MODELS = [m.strip() for m in os.getenv("MODELS", "").split(",") if m.strip()]


def precache_tiktoken() -> None:
    print("\n=== Pre-caching tiktoken encoding ===")
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        enc.encode("warmup")
        print(f"OK — cached under {os.environ['TIKTOKEN_CACHE_DIR']}")
    except Exception as exc:  # pragma: no cover
        print(f"FAILED to cache tiktoken encoding: {exc}")


def test_model(client: httpx.Client, model: str) -> tuple[str, str]:
    """Send one minimal real request to `model`. Returns (status, detail)."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
    }
    try:
        resp = client.post(
            f"{BASE_URL}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=30,
        )
        if resp.status_code == 200:
            return "PASS", "200 OK"
        return "FAIL", f"HTTP {resp.status_code}: {resp.text[:150]}"
    except Exception as exc:
        return "FAIL", str(exc)[:150]


def run_model_smoke_tests() -> list[tuple[str, str, str]]:
    print("\n=== Testing all models from Participant Handbook (MODELS in .env) ===")
    if not MODELS:
        print("No MODELS configured in .env — nothing to test.")
        return []

    results = []
    # verify=False: corporate network SSL bypass (self-signed / MITM proxy certs).
    with httpx.Client(verify=False) as client:
        for model in MODELS:
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

    if results and any(s == "FAIL" for _, s, _ in results):
        sys.exit(1)
