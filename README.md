# OpsFlow

**AI-verified operations console for IT application maintenance.**

A supervised team of AI agents that turns patching, performance tuning, and incident resolution
into one repeatable, auditable workflow — from "an alert (or voice note, or screenshot) came in"
to "ticket closed, CMDB updated, and a verified fix, not just an assumed one."

Built for **TCS AI Fridays Season 2 — Regional Round**
(*Problem statement: AI-Powered Multi-Agent Workflow Automation for IT Application Maintenance*).

**🔗 Live demo:** [opsflowapp.onrender.com](https://opsflowapp.onrender.com)

No API key needed to try it — the login screen opens with an **Instant Demo** mode using
pre-generated output, plus options to bring your own key or use a shared free key. See
[§8 Try it live](#8-try-it-live--testing-modes) below.

> New to this repo? Read this file top to bottom once — it gets you from a fresh clone to a
> running app. Everything else you might want is linked from [§7 Learn more](#7-learn-more) below.

---

## 1. What this actually is

- A **FastAPI backend** running a 9-step supervised agent chain (Correlate → Enrich → Diagnose →
  Plan → Gate → Approve → Execute → Verify → Sync → Knowledge) over three workflow types
  (incident / patch / performance).
- A **Next.js frontend** ("the OpsFlow cockpit") — a role-based ops console with a live alert
  feed, an incident workspace, a full agent-trace viewer, and a floating chat assistant that
  accepts text, voice, and screenshot uploads.
- **No real third-party systems.** "ServiceNow" and "Jira" panels you'll see are FastAPI
  simulators this project wrote itself.
- **Multi-provider LLM architecture** (`backend/providers.py`): Google Gemini by default, OpenRouter
  as a fallback, and the original TCS GenAI Lab gateway kept as a legacy/gated provider (only
  reachable from the TCS network) — plus a local Ollama model for the PII/secrets scrubber and as
  an offline fallback if the active provider fails mid-request. Which provider backs a given
  session depends on the testing mode chosen at login (§8) — never a mix of vendors within one
  session, and a visitor's own Bring-Your-Own-Key never touches the server.
- **100% synthetic data** — generated with a fixed seed, provenance-tracked in `data/PROVENANCE.md`.

Full architecture, data flow, demo script, and folder-by-folder guide: see [§7](#7-learn-more).

---

## 2. Prerequisites — exact versions that are known to work

| Tool | Version | Notes |
|---|---|---|
| **Python** | 3.12.x (this project was built/tested on 3.12.8) | 3.11 likely works too; avoid 3.13 until you've confirmed `chromadb`/`langchain` compatibility yourself |
| **Node.js** | **20.9 or newer** (20.x LTS or 22.x LTS recommended) | Next.js 16 refuses to install below this — you'll get an `EBADENGINE` error otherwise |
| **npm** | ships with Node | On Windows PowerShell, use `npm.cmd`, not `npm` (see [Troubleshooting](#troubleshooting)) |
| **Ollama** | any recent version | Must already have `llama-3.2-3b-it` and `gte-large` pulled — used for the PII scrubber and the offline fallback. Run `ollama list` to check; **do not download new models on an event/restricted network** |
| **Git** | any recent version | Only needed if you're cloning rather than copying the folder |
| **A TCS GenAI Lab gateway API key** | — | Issued per-event; without it the app still runs, but every LLM step will fall back to local Ollama (slower, and the scrubber-only model isn't a substitute for the reasoning/planning models) |

**OS note:** this project was built and is documented for **Windows** (PowerShell). Mac/Linux
should work with the equivalent shell commands, but the corporate-proxy SSL workarounds baked
into `backend/config.py` are a no-op (not harmful) if you don't need them.

---

## 3. Get the code

```powershell
git clone <this-repo-url> my-hackathon-app
cd my-hackathon-app
```
(If you already have the folder — e.g. it was shared as a zip — just `cd` into it; skip cloning.)

---

## 4. Backend setup

```powershell
cd backend

# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies (pinned versions — see backend/requirements.txt)
pip install -r requirements.txt

# 3. Configure environment variables
copy .env.example .env
# now open backend\.env and fill in BASE_URL / API_KEY (your gateway credentials) —
# see backend/.env.example for what every key means and a working default shape

# 4. Build the SQLite database (only needed once, or after data/app.db is deleted)
python db\init_db.py

# 5. Build the Chroma vector store (runbooks/postmortems/tickets — needs a working gateway
#    connection, since it calls the real embedding model)
python db\load_chroma.py

# 6. (Optional but recommended first time) confirm the gateway + Ollama + models all actually work
python smoke_test.py

# 7. Run the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8765
```

Leave this terminal running. You should see `Application startup complete.` and no errors.
Verify it's alive: open **http://localhost:8765/health** in a browser — expect a `200 OK` JSON
response.

> **Port 8765, not 8000/8001.** Windows silently blocks binds to those ports on some machines
> (Hyper-V/WSL reserved ranges) — see [Troubleshooting](#troubleshooting).

### If steps 4/5 are already done for you
If `data/app.db` and `data/chroma_db/` already exist and look populated (e.g. you received this
project pre-built, not a fresh clone), you can skip steps 4-5 and go straight to step 7. Re-run
`db/init_db.py`/`db/load_chroma.py` any time you want a clean, from-scratch database.

---

## 5. Frontend setup

Open a **second** terminal (leave the backend running in the first one):

```powershell
cd frontend

# 1. Install dependencies
npm.cmd install

# 2. Configure environment variables
copy .env.local.example .env.local
# defaults to http://localhost:8765 — only change this if your backend runs on a different port

# 3. Run the dev server
npm.cmd run dev
```

Open **http://localhost:3000** — you should land on the OpsFlow login screen.

---

## 6. Log in and confirm it works

Three demo accounts are seeded automatically by `db/init_db.py` (one per role):

| Username | Password | Role |
|---|---|---|
| `alex.chen` | `OpsEngineer!123` | Ops Engineer |
| `priya.sharma` | `Approver!123` | Approver |
| `admin` | `Admin!123` | Admin |

Log in as `admin` first — it can see every panel (Users, Config, Scenarios, Audit Log, Knowledge
Base) in the sidebar, useful for verifying the whole stack came up correctly. You should see:
- The **Overview** tab with real (non-zero, if any runs have happened) or zero-but-not-erroring
  metric tiles.
- The **Ops Board** tab showing a live-updating connection indicator (SSE feed from the backend).
- The **Autonomy Ladder** tab listing runbooks (confirms both the DB and the seed data loaded).

If all three render without errors, the full stack is working end to end.

### Try one real workflow run
Sidebar → **Scenarios** panel (Admin/Approver) → launch `SCEN-01` (a clean, auto-approved incident
resolution). It should reach `verified_resolved` within roughly the time it takes DeepSeek R1 to
respond (can be 10-40+ seconds on a busy gateway — this is expected, not a hang). See
`DEMO_SCRIPT.md` for the full scenario list and what each one demonstrates.

---

## 7. Learn more

This README gets you running. For everything else:

| Doc | What's in it |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System design: tiers, the 9-step agent chain, models used, guardrails, protocols, storage |
| [`APP_FLOW.md`](APP_FLOW.md) | End-to-end data flow, sequence diagrams, where every UI number comes from |
| [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) | Jury pitch, use-case story, live demo click-path, all 6 scenario fixtures explained |
| [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) | Folder-by-folder / file-by-file guide to the whole codebase |
| [`SETUP.md`](SETUP.md) | This README's detailed companion — full environment variable reference, troubleshooting appendix, verification checklist |
| [`PRD_FINAL.md`](PRD_FINAL.md) | The frozen product requirements this build satisfies (long — reference, not required reading) |
| [`.knowledge/`](.knowledge/) | The build's own engineering log (architecture-as-built detail, decisions, phase-by-phase history) — useful if you're extending the code, not needed to just run it |
| [`.okf/`](.okf/) | Portable Open Knowledge Format bundle — the same system knowledge as `.knowledge/`, distilled into one-concept-per-file markdown for readers without this repo's session history. Start at `.okf/index.md`. |

---

## 8. Try it live / testing modes

The login screen offers three ways to try OpsFlow — no account or key required just to look
around:

| Mode | What it needs | What it does |
|---|---|---|
| **Instant Demo** | Nothing | Replays 6 pre-generated scenario runs (`data/demo_outputs.json`, built by `scripts/pregenerate_demo_outputs.py`) plus a real, unmodified-pipeline PII-scrubbing sample — zero live model calls, always works. Ad-hoc chat, voice, and image intake are disabled with an inline explanation; the full agent-chain UI (Agent Trace, evidence, blast radius, approval flow) still renders from real (pre-captured) data. |
| **Bring Your Own Key** | Your own key for Google Gemini, OpenAI, OpenRouter, xAI Grok, the legacy TCS gateway, or any custom OpenAI-compatible endpoint | Sent as request headers (`X-LLM-Provider`/`X-LLM-Api-Key`/`X-LLM-Model`), used only for that browser session, never written to disk or logged. The login screen validates the key/model against the real provider before letting you into the cockpit — a bad key surfaces the provider's real error inline instead of failing later. Voice intake is only available if the chosen provider supports transcription (OpenAI, TCS; for a custom endpoint this is actually checked live rather than guessed — see `providers.py`'s `probe_transcription_support()`). |
| **Free Demo Key** | Nothing (uses a key the deployer configured) | Live diagnosis backed by a Gemini key set as a platform secret, with the same offline-Ollama-fallback resilience the app already has for gateway outages. |

Real login still happens either way — role quick-fill buttons on the login screen fill in one of
the seeded demo accounts (§6 above) so you can prove sign-in works without hunting for credentials.

**A note on free-tier limits** (found live-testing this): Gemini's free tier caps some models at a
literal 20 requests/day (`gemini-flash-latest`'s "thinking" alias) — `providers.py` deliberately
routes every Gemini role through `gemini-flash-lite-latest` instead, which doesn't hit that wall
and doesn't truncate structured JSON output under a capped token budget the way the reasoning
alias does. Embeddings have a separate, more generous per-minute quota; `orchestrator/retrieval.py`
retries with a full-minute backoff on a 429 rather than failing the request.

---

## 9. Deploying your own copy

One platform, two free service types on [Render](https://render.com) — a Web Service for the
backend (needs a long-running process: SQLite + Chroma opened once and held across requests, plus
an SSE stream) and a Static Site for the frontend (zero server-side routes, so it gets a strictly
better free tier: always-warm, CDN-backed, no idle-sleep). `render.yaml` at the repo root defines
both as a Render Blueprint.

1. Push this repo to your own GitHub account (public or private — Render's free tier works with
   either).
2. On Render: **New +** → **Blueprint**, connect the repo. Render reads `render.yaml` and proposes
   both services (`opsflowapp-backend`, `opsflowapp`) — rename them in `render.yaml` first if you
   want different names; Render silently appends a random suffix to whichever ones are already
   taken by another account, which is exactly what happened on the first deploy of this project
   (fixed 2026-08-15 by recreating both services directly via Render's API under names that turned
   out to be free).
3. Fill in the secrets it asks for before creating: `GEMINI_API_KEY` (required — backs both
   embeddings and Free Demo Key mode; get one free at aistudio.google.com/apikey) and
   `OPENROUTER_API_KEY` (optional — only needed if you want that as a working Free/BYOK fallback
   option). `JWT_SECRET`/`A2A_SECRET` auto-generate; leave `FRONTEND_ORIGIN` and
   `NEXT_PUBLIC_API_BASE_URL` blank for now — their real values aren't known until both services
   exist.
4. Once both are created, note their actual `*.onrender.com` URLs (Render appends a suffix if your
   chosen name is taken by someone else). Set:
   - The backend's `FRONTEND_ORIGIN` → the frontend's URL, then trigger a manual restart (no
     rebuild needed — read from the environment at request time).
   - The frontend's `NEXT_PUBLIC_API_BASE_URL` → the backend's URL, then trigger a manual
     **deploy** (rebuild needed — Next.js bakes `NEXT_PUBLIC_*` values into the static bundle at
     build time, per `output: "export"` in `next.config.mjs`).
5. Visit the frontend's URL, confirm `/health` on the backend responds, and run one Instant Demo
   scenario end to end before calling it done.

The backend's free tier sleeps after 15 minutes idle (~1 min cold-start on the next request) and
has no persistent disk — SQLite/Chroma rebuild fresh from the committed synthetic seed data on
every boot, so this is expected, not a bug (see `render.yaml`'s comments). The frontend never
sleeps.

---

## Troubleshooting

The most common first-run issues, and their fixes:

- **`pip install` fails with a `ResolutionImpossible` / numpy conflict** — you're likely on a
  Python version where `langchain==0.3.7` and a newer `numpy` can't co-exist. Use Python 3.12 and
  the exact `requirements.txt` as pinned; don't upgrade individual packages by hand.
- **Backend won't bind / silently exits, no errors** — something is already listening on port
  8765 from a previous run. Find and stop it (`netstat -ano | findstr :8765` on Windows, then
  `taskkill /PID <pid> /F`), then restart `uvicorn`.
- **`npm install` / `npm run dev` fails with a PowerShell script-execution error** — use `npm.cmd`
  instead of `npm` in PowerShell.
- **Frontend loads but every API call fails / CORS errors in the console** — check that
  `frontend/.env.local`'s `NEXT_PUBLIC_API_BASE_URL` and `backend/.env`'s `FRONTEND_ORIGIN`
  actually point at each other's real host/port.
- **`uvicorn` crashes on `python-multipart`** — already pinned in `requirements.txt`; if you edited
  it, this is why login and file-upload routes break.
- **Diagnose/Plan steps take a long time or seem to hang** — DeepSeek R1 genuinely takes tens of
  seconds on a busy gateway; this is expected latency on one step, not a bug. If the gateway is
  fully unreachable, the app should still complete via the local Ollama fallback (slower).
- **`ollama` fallback errors** — run `ollama list` and confirm `llama-3.2-3b-it` and `gte-large`
  are present; if not, get them from whoever manages the lab machine rather than pulling new
  models on a restricted network.

For anything not listed here, `.knowledge/errors-solved.md` has a longer, more detailed log of
every real error hit while building this project and exactly how it was fixed.

---

## A note on data & privacy

Every dataset in `data/` (alerts, tickets, CMDB, runbooks, postmortems) is synthetic — generated
by this project's own scripts, never scraped or copied from a real system. Where the demo shows
"planted" personal data or secrets (names, phone numbers, connection strings, API keys), it exists
specifically to prove the PII/secret scrubber works, and is tracked in
`data/pii_ground_truth.json` for that purpose. See `.knowledge/domain-privacy.md` for the full
rationale.
