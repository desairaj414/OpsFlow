---
type: reference
title: Environment & Network
status: active
updated: 2026-08-16
related: [errors-solved.md, ../architecture/models-routing.md]
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

# 2. Corporate-proxy SSL bypass — GATED, not unconditional. Only applies when TCS_NETWORK=true
# (backend/.env), since the public deploy has no corporate MITM proxy and disabling verification
# globally there would be an unforced security regression. See config.py lines ~10-35.
if TCS_NETWORK:                                    # os.getenv("TCS_NETWORK", "false").lower() == "true"
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context

    import requests
    _orig_request = requests.Session.request
    def _unverified_request(self, *args, **kwargs):
        kwargs["verify"] = False
        return _orig_request(self, *args, **kwargs)
    requests.Session.request = _unverified_request
```
Per-provider SSL bypass for the `tcs` provider's own outbound calls (e.g. `httpx.Client(verify=False)`)
is handled independently, per-client, in `api_client.py` — separate from the global gate above.

## Endpoint — multi-provider, not a single endpoint
`backend/providers.py` is a 6-provider registry (Gemini default, OpenRouter fallback, TCS retained
as a gated legacy option, plus others) — the TCS GenAI Lab gateway below is now just one option
within it, not the app's sole endpoint. Full provider list, selection logic, and BYOK/Free-Demo-Key
routing: `.okf/architecture/provider-registry.md` (not duplicated here).

**`tcs` provider config** (`backend/.env`):
- `BASE_URL` — `https://genailab.tcs.in/v1`
- `API_KEY` — gateway key. **Never copy the key value into `.knowledge/` files, reference by key name only.**
- Only reachable/enabled when `TCS_NETWORK=true` (see above) — corporate network only.

**Other provider env keys** (`backend/.env`, see `backend/.env.example`):
- `DEFAULT_PROVIDER` — which provider a request uses with no `X-LLM-Provider` header (`gemini` for
  the public deploy, `tcs` for local dev against the original TCS gateway).
- `GEMINI_API_KEY` — Gemini provider key.
- `OPENROUTER_API_KEY` — OpenRouter provider key; also `api_client.py`'s fallback if Gemini fails
  during a Free Demo Key session (never falls back to a visitor's own BYOK key).
- `TCS_NETWORK` — boolean, default `false`. Gates the SSL-bypass monkeypatching above and whether
  the `tcs` provider is reachable at all.

## Models available (from `backend/.env` → `MODELS`, confirmed reachable at least once)
24/32 chat-capable models PASS per current smoke test. Handbook-relevant subset (see
[citations.md](citations.md) and [models-routing.md](../architecture/models-routing.md) for the full routing mapping):
`azure/genailab-maas-gpt-4o-mini`, `genailab-maas-DeepSeek-V3-0324`, `azure_ai/genailab-maas-DeepSeek-R1`,
`azure_ai/genailab-maas-Llama-3.2-90B-Vision-Instruct`, `azure_ai/genailab-maas-Phi-4-reasoning`,
`azure/genailab-maas-whisper` (alt `azure/gpt-realtime-whisper`), `azure/genailab-maas-text-embedding-3-large`.
**Whisper and Llama Vision are BLOCKING checks per PRD Phase 0 step 2 — confirm each explicitly, not just via the general 24/32 sweep.**

## Local Ollama
- Run `ollama list` and record exact model names/sizes (see `.knowledge/TCS_HACKATHON_FINDINGS.md`
  for the original recorded set). **Never download new models.**

## Network / proxy notes
- Corporate (TCS) network requires SSL verification bypass (`verify=False`) everywhere outbound —
  but only there. Gated behind `TCS_NETWORK=true`; the public deploy runs with it off. See "Mandatory fixes" above.
- `TIKTOKEN_CACHE_DIR` must point locally (`./token`) since HF/tiktoken downloads are blocked; a token cache dir already exists at `backend/token/`.

## Ports
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8765` — **not 8000/8001**, see `errors-solved.md` (Windows reserves those ephemeral ranges)
- `frontend/.env.local` → `NEXT_PUBLIC_API_BASE_URL` must match the backend port above (see
  `frontend/.env.local.example`; the old Vite app's `frontend/.env` → `VITE_API_BASE_URL` is gone
  post-migration).
- MCP simulator default ports (production mode; the app itself wires all of these in-process via
  `orchestrator/mcp_wiring.py`, so these only matter if a simulator is run standalone):
  Monitoring 9001, ITSM 9002, Tracker 9003, CMDB 9004, **Patch Source 9005** (added for Patch
  Management, `mcp_servers/simulators/patch_source.py`).

## Deployment — Render (live)
Both services deploy to Render as a Blueprint via `render.yaml` at repo root: `opsflowapp-backend`
(Python Web Service) and `opsflowapp` (static-exported Next.js site). Live URLs:
`https://opsflowapp-backend.onrender.com` (backend) and `https://opsflowapp.onrender.com`
(frontend). Full rationale (why Render-only, why not Vercel+Render, the `opsflow-*` →
`opsflowapp*` rename) lives in `.okf/decisions/hosting-platform.md` — not duplicated here.

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
