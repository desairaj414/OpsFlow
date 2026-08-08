# Verascope — Requirements & Setup Reference

Detailed companion to `README.md`'s quick start. Read this if the quick start didn't work, if you
need the exact dependency list before installing anything, or if you're setting this up on a
machine you don't fully control (a shared lab laptop, a fresh VM, etc).

---

## 1. System requirements

| Requirement | Version | How to check | How to get it |
|---|---|---|---|
| Python | **3.12.x** (tested on 3.12.8) | `python --version` | [python.org/downloads](https://www.python.org/downloads/) |
| Node.js | **20.9+** (20.x or 22.x LTS) | `node --version` | [nodejs.org](https://nodejs.org/) |
| npm | bundled with Node | `npm --version` | bundled with Node |
| Ollama | any recent release, already running as a local service | `ollama list` | pre-installed on event lab machines — **do not install/pull new models on a restricted network without checking first** |
| Disk space | ~2 GB free | — | dependencies (`node_modules`, Python venv) + the Chroma vector store |
| Network | outbound HTTPS to `genailab.tcs.in` (or your gateway host) | — | corporate/event network may require the SSL-bypass workarounds already built into `backend/config.py` — no action needed from you |

Two Ollama models must already be pulled locally (confirm with `ollama list`):
- `llama-3.2-3b-it` — used by the PII/secret scrubber and as the offline chat fallback
- `gte-large` — used as the offline embeddings fallback

If either is missing, get it from whoever manages the machine/network — don't `ollama pull` blind
on an event network with limited bandwidth.

---

## 2. What gets installed — the actual dependency lists

### Backend (`backend/requirements.txt`)
```
fastapi==0.115.0            # web framework
uvicorn[standard]==0.30.6   # ASGI server
httpx==0.27.2                # async HTTP client (gateway calls)
requests==2.32.3              # sync HTTP (tiktoken's internal downloader needs this patched)
python-multipart==0.0.9        # required for form-based login (OAuth2PasswordRequestForm)
langchain==0.3.7                # LLM orchestration / .with_fallbacks() offline routing
langchain-openai==0.2.6           # OpenAI-compatible chat/embeddings client
tiktoken==0.8.0                    # tokenizer
python-dotenv==1.0.1                 # loads backend/.env
python-jose[cryptography]==3.3.0      # mock JWT signing/verification
pydantic==2.9.2                        # typed contracts (MaintenanceSignal, SpecialistResult, ...)
chromadb==0.5.20                        # vector store (runbooks/postmortems/tickets/negative-KB)
scikit-learn==1.5.2                      # DBSCAN alert correlation
pandas==2.2.3                             # metric CSV handling
numpy==1.26.4                              # pinned <2.0 — langchain 0.3.7 requires this on Python 3.12
faker==30.8.2                               # synthetic data generation
mcp==1.9.4                                   # Model Context Protocol servers (needs >=1.2 for FastMCP)
pytest==8.3.3                                 # test suite
pyyaml==6.0.3                                  # declarative workflow YAML (incident/patch/performance)
pillow==11.0.0                                  # image handling for the vision intake path
```
**Do not upgrade these individually.** Several are pinned together deliberately (see
`.knowledge/errors-solved.md` for the exact numpy/langchain conflict that pinning avoids).

### Frontend (`frontend/package.json`)
```
next            16.3.0     # framework (App Router)
react           19.2.8
react-dom       19.2.8
lucide-react    ^1.29.0    # icon set
clsx / tailwind-merge      # className utilities
tailwindcss     ^4         # styling (dev dependency)
eslint / eslint-config-next ^9 / 16.3.0   # linting (dev dependency)
```

---

## 3. Step-by-step install (detailed)

### 3.1 Backend

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
Confirm the venv is actually active — your prompt should show `(venv)`. If `pip install` fails,
see [§5 Troubleshooting](#5-troubleshooting) before trying anything else.

```powershell
copy .env.example .env
```
Open `backend\.env` and fill in real values. Every key is documented inline in
`backend\.env.example` — the two you must set yourself are `BASE_URL` and `API_KEY` (your TCS
GenAI Lab gateway credentials). Everything else has a working default.

**Build the databases** (once, or whenever you want a clean reset):
```powershell
python db\init_db.py          # creates data\app.db from schema.sql + generated JSON/CSV data
python db\load_chroma.py      # embeds runbooks/postmortems/tickets into data\chroma_db (needs a working gateway connection — uses the real embedding model)
```
Both scripts accept a `--test` flag that also runs a self-check:
```powershell
python db\init_db.py --test
python db\load_chroma.py --test
```

**Smoke-test the gateway + models** (optional, but catches a bad API key immediately instead of
mid-demo):
```powershell
python smoke_test.py          # fast: checks the ~6 models this app actually uses, plus Whisper/vision/embeddings
python smoke_test.py --full   # slow: sweeps every model listed in MODELS, only for a periodic full audit
```

**Run the server:**
```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8765
```
Confirm: `http://localhost:8765/health` returns `200 OK`.

### 3.2 Frontend

```powershell
cd frontend
npm.cmd install
copy .env.local.example .env.local
npm.cmd run dev
```
Confirm: `http://localhost:3000` shows the Verascope login screen, and the browser console has no
red CORS errors.

### 3.3 Run the backend test suite (optional, confirms everything wired correctly)
```powershell
cd backend
venv\Scripts\activate
pytest
```
Expect all tests green (98+ at last count) — a real, working gateway connection is required for
the full suite since several tests exercise real LLM/embedding calls, not mocks.

---

## 4. Environment variable reference

### `backend/.env`
| Key | Required? | Default | Meaning |
|---|---|---|---|
| `BASE_URL` | yes | `https://genailab.tcs.in/v1` | Gateway base URL (OpenAI-compatible) |
| `API_KEY` | yes | *(empty)* | Your gateway API key — without it every LLM call fails over to local Ollama |
| `MODELS` | recommended | *(empty)* | Comma-separated model ids `smoke_test.py --full` sweeps |
| `DEFAULT_CHAT_MODEL` | recommended | first of `MODELS` | Fallback default if a specific agent doesn't hardcode one |
| `DEFAULT_EMBED_MODEL` | recommended | *(empty)* | Must be an embedding-capable model id |
| `OLLAMA_BASE_URL` | no | `http://localhost:11434/v1` | Local Ollama's OpenAI-compatible endpoint |
| `OLLAMA_FALLBACK_CHAT_MODEL` | no | `llama-3.2-3b-it` | Used only if a gateway chat call fails |
| `OLLAMA_FALLBACK_EMBED_MODEL` | no | `gte-large` | Used only for a hand-rolled embeddings fallback (not wired into live RAG retrieval — see `.knowledge/models-routing.md`) |
| `FRONTEND_ORIGIN` | yes | `http://localhost:3000` | CORS allow-origin — must match where the frontend actually runs |
| `JWT_SECRET` | yes for anything beyond local demo | `dev-only-change-me` | Signs the mock login JWT |
| `JWT_EXPIRE_MINUTES` | no | `60` | Session length |
| `A2A_SECRET` | yes for anything beyond local demo | `dev-only-change-me-a2a` | Signs the A2A Agent Card (Supervisor → Diagnosis handoff) |

### `frontend/.env.local`
| Key | Required? | Default | Meaning |
|---|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | yes | `http://localhost:8765` | Where the frontend sends every API call — must match the backend's actual host/port |

---

## 5. Troubleshooting

Ordered roughly by how early in setup they tend to bite.

| Symptom | Root cause | Fix |
|---|---|---|
| `pip install -r requirements.txt` → `ResolutionImpossible` mentioning numpy | A newer numpy was requested/installed alongside `langchain==0.3.7`, which requires numpy `<2.0` on Python 3.12 | Use the exact pinned versions in `requirements.txt`; don't `pip install -U numpy` separately |
| `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` | An old `mcp` version installed (pre-1.2, before `FastMCP` existed) | Confirm `mcp==1.9.4` is what actually installed: `pip show mcp` |
| `RuntimeError: Form data requires "python-multipart"` on login | Missing dependency | `pip install python-multipart` (already in `requirements.txt` — re-run `pip install -r requirements.txt` if you edited it) |
| `SSLCertVerificationError` during `smoke_test.py`/`load_chroma.py` | Corporate proxy MITM breaks tiktoken's internal downloader | Already patched in `config.py`/`load_chroma.py` — make sure you didn't remove the `TIKTOKEN_CACHE_DIR` + SSL monkeypatch lines at the top of the file you're running |
| Backend fails to bind, or edits don't seem to take effect after restart | Windows reserves ephemeral port ranges around 8000/8001; separately, a stale `uvicorn` process can hold port 8765 | Always run on `--port 8765`; if edits aren't showing up, find and kill the old process: `netstat -ano \| findstr :8765`, then `taskkill /PID <pid> /F` |
| `npm install` / `npm run dev` fails with a PowerShell execution-policy error | PowerShell blocks the `npm` `.ps1` shim by default | Use `npm.cmd install` / `npm.cmd run dev` instead of bare `npm` |
| `npm install` fails with `EBADENGINE` | Node.js below 20.9 | Upgrade Node — Next.js 16 will not install on Node 18 |
| Frontend loads, but every API call fails silently or shows CORS errors | `NEXT_PUBLIC_API_BASE_URL` (frontend) and `FRONTEND_ORIGIN` (backend) don't point at each other | Check both `.env` files match your actual ports |
| A workflow run seems to hang for 30-60+ seconds | Expected — DeepSeek R1 (the Diagnose step) genuinely takes tens of seconds on a busy gateway; this is real latency, not a bug | Wait it out, or watch the Agent Trace panel's per-step timer once it completes |
| Everything falls back to Ollama even though the gateway should be up | Wrong/expired `API_KEY`, or `BASE_URL` typo'd | Run `python smoke_test.py` — it isolates exactly which check fails and why |
| A `/chunks` or Plan-step query intermittently throws `Cannot return the results in a contigious 2D array` | A known Chroma/hnswlib limit under concurrent queries on the same collection, already mitigated (`hnsw:search_ef=500`) but not eliminated under heavy concurrent load | Retry the action; if it's frequent, see `.knowledge/errors-solved.md` for the full root-cause writeup |

For anything not covered above, `.knowledge/errors-solved.md` has the complete, dated log of every
real error encountered while building this project, with root cause and exact fix — more detail
than fits here.

---

## 6. Verification checklist

Run through this once after setup to confirm everything is actually wired correctly, not just
"started without crashing":

- [ ] `GET http://localhost:8765/health` returns `200`
- [ ] `python smoke_test.py` passes for the handbook models, Whisper, vision, and embeddings
- [ ] Frontend login screen loads at `http://localhost:3000` with no console errors
- [ ] Logging in as `admin` (`Admin!123`) shows all 5 tabs + all 5 sidebar panels
- [ ] Ops Board shows a green/live SSE connection indicator
- [ ] Autonomy Ladder tab lists runbooks (confirms `db/init_db.py` seeded correctly)
- [ ] Knowledge Base sidebar panel shows chunked runbook content (confirms `db/load_chroma.py` ran
      and the gateway embedding call actually succeeded)
- [ ] Launching scenario `SCEN-01` from the Scenarios panel reaches `verified_resolved`
- [ ] `pytest` (from `backend/`, venv active) passes

If all of these pass, the environment is demo-ready.
