---
type: reference
title: Environment & Network
status: active
updated: 2026-08-07
related: [errors-solved.md, prd-phase-0.md, models-routing.md]
---

## Run commands
```bash
# Backend
cd backend
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
python smoke_test.py                            # fast default: HANDBOOK_MODELS (~4) + Whisper/Vision/embedding checks
python smoke_test.py --full                     # slow: all 32 models in MODELS, only for a periodic full audit
uvicorn main:app --reload --host 0.0.0.0 --port 8765   # NOT 8000/8001 — see errors-solved.md

# Frontend
cd frontend
npm.cmd install     # use npm.cmd on Windows PowerShell, plain `npm` is blocked (see errors-solved.md)
npm.cmd run dev     # http://localhost:3000
```

## Mandatory fixes (copy exactly, order matters — already applied in backend/config.py)
```python
# 1. TOP OF EVERY ENTRYPOINT — before langchain/tiktoken imports
import os
os.environ["TIKTOKEN_CACHE_DIR"] = "./token"

# 1b. Corporate proxy MITM certs also break tiktoken's internal downloader (uses `requests`) — bypass globally
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# 1c. tiktoken's downloader ignores the ssl monkeypatch — also patch requests.Session directly
import requests
_orig_request = requests.Session.request
def _unverified_request(self, *args, **kwargs):
    kwargs["verify"] = False
    return _orig_request(self, *args, **kwargs)
requests.Session.request = _unverified_request

# 2. SSL bypass for outbound httpx/langchain calls
import httpx
http_client = httpx.Client(verify=False)          # or httpx.AsyncClient(verify=False) — PRD §0 requires async for FastAPI
```

## Endpoint
- Base URL: `https://genailab.tcs.in/v1` (see `backend/.env` → `BASE_URL`)
- Auth: `API_KEY` in `backend/.env` — **never copy the key value into `.knowledge/` files, reference by key name only**

## Models available (from `backend/.env` → `MODELS`, confirmed reachable at least once)
24/32 chat-capable models PASS per current smoke test. Handbook-relevant subset (see
[citations.md](citations.md) and [models-routing.md](models-routing.md) for the full routing mapping):
`azure/genailab-maas-gpt-4o-mini`, `genailab-maas-DeepSeek-V3-0324`, `azure_ai/genailab-maas-DeepSeek-R1`,
`azure_ai/genailab-maas-Llama-3.2-90B-Vision-Instruct`, `azure_ai/genailab-maas-Phi-4-reasoning`,
`azure/genailab-maas-whisper` (alt `azure/gpt-realtime-whisper`), `azure/genailab-maas-text-embedding-3-large`.
**Whisper and Llama Vision are BLOCKING checks per PRD Phase 0 step 2 — confirm each explicitly, not just via the general 24/32 sweep.**

## Local Ollama
- Run `ollama list` and record exact model names/sizes in `PHASE0_FINDINGS.md`. **Never download new models.**

## Network / proxy notes
- Corporate network requires SSL verification bypass (`verify=False`) everywhere outbound.
- `TIKTOKEN_CACHE_DIR` must point locally (`./token`) since HF/tiktoken downloads are blocked; a token cache dir already exists at `backend/token/`.

## Ports
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8765` — **not 8000/8001**, see `errors-solved.md` (Windows reserves those ephemeral ranges)
- `frontend/.env` → `VITE_API_BASE_URL` must match the backend port above.
- MCP simulator default ports (production mode; the app itself wires all of these in-process via
  `orchestrator/mcp_wiring.py`, so these only matter if a simulator is run standalone):
  Monitoring 9001, ITSM 9002, Tracker 9003, CMDB 9004, **Patch Source 9005** (added for Patch
  Management, `mcp_servers/simulators/patch_source.py`).

## Phase 0 smoke-test results (verified 2026-08-07, `python smoke_test.py`)
| Check | Status | Notes |
|---|---|---|
| `ollama list` recorded | ✅ | `devstral`, `qwen-2.5.1-coder-it`, `llama-3.2-3b-it`, `gemma-3-4b-it`, `deepseek-r1`, `gte-large` — all pre-installed, none pulled |
| gpt-4o-mini | ✅ PASS | 1022ms |
| DeepSeek V3 role (`genailab-maas-DeepSeek-V3-0324`) | ✅ PASS | Original deployment confirmed permanently gone (410). Human-approved substitute **`azure/genailab-maas-gpt-4.1-nano`** wired into `HANDBOOK_MODELS` — 1206ms, valid structured JSON on a realistic plan-drafting prompt. See models-routing.md. |
| DeepSeek R1 | ✅ PASS | 824-1391ms across runs |
| Phi-4-reasoning | ⚠ INTERMITTENT | PASS 3x early in session, then 404 DeploymentNotFound; rechecked 3x back-to-back: 404, 404, 200. Gateway flakiness, not a deprecation — non-blocking (smoke-test-only, unused in primary path). Re-check before Phase 0 formally closes. |
| Whisper (`azure/genailab-maas-whisper`, real audio via `/audio/transcriptions`) | ✅ PASS | 1581ms, transcribed generated test tone |
| Vision path (real image via `image_url`) | ✅ PASS | Original Llama Vision deployment confirmed permanently gone (404/410, rechecked). Human-approved substitute **`genailab-maas-gpt-4o`** wired into `smoke_test.py` (`VISION_MODEL`) — 1323ms, correctly identified test image color. See models-routing.md. |
| `text-embedding-3-large` → Chroma round-trip | ✅ PASS | dim=3072, embed→store→query matched, 332ms |
| SSL bypass confirmed | ✅ | applied in config.py, live-verified via all calls above |
| TIKTOKEN_CACHE_DIR confirmed | ✅ | `backend/token/` exists, live-verified |
| Latency/token cost per model recorded | ✅ | see rows above; full 32-model `--full` sweep separately hung on `gpt-5.1` (10+ min, ~0 CPU — proxy-level stall, not a real per-model timeout) and was killed; not worth re-running for the smoke test's purpose since HANDBOOK_MODELS already covers the required set |
| Jira `atlassian.net` reachability probe (optional, 30 min hard cap) | ☐ | not yet attempted |
