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
python smoke_test.py                            # run FIRST, every session start
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

## Phase 0 smoke-test results (fill in as Phase 0 steps are verified)
| Check | Status | Notes |
|---|---|---|
| `ollama list` recorded | ☐ | |
| All 7 handbook models reachable (incl. Whisper, Llama Vision — blocking) | ☐ | 24/32 broader sweep already PASS |
| SSL bypass confirmed | ✅ | applied in config.py |
| TIKTOKEN_CACHE_DIR confirmed | ✅ | `backend/token/` exists |
| Latency/token cost per model recorded | ☐ | |
| `text-embedding-3-large` → Chroma round-trip | ☐ | |
| Jira `atlassian.net` reachability probe (optional, 30 min hard cap) | ☐ | |
