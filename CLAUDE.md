# CLAUDE.md — Project Index

## Project
- **Name:** my-hackathon-app
- **Stack:** FastAPI (backend) + Vite/React + shadcn/ui + Tailwind (frontend)
- **LLM Endpoint:** TCS GenAI Lab (OpenAI-compatible) — `https://genailab.tcs.in`
- **Problem Statement:** TBD at event. See `PRD_DRAFT.md` → `PRD_FINAL.md`.

## Run Commands
```bash
# Backend
cd backend
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
python smoke_test.py                            # run FIRST when API key arrives
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev                                     # http://localhost:3000
```

## Mandatory Fixes (copy exactly, order matters)
```python
# 1. TOP OF EVERY ENTRYPOINT — before langchain/tiktoken imports
import os
os.environ["TIKTOKEN_CACHE_DIR"] = "./token"

# 1b. Corporate proxy MITM certs also break tiktoken's internal downloader — bypass globally
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# 2. SSL bypass for corporate proxy/MITM certs (outbound httpx/langchain calls)
import httpx
http_client = httpx.Client(verify=False)

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
llm = ChatOpenAI(base_url=BASE_URL, api_key=API_KEY, http_client=http_client, model=MODEL_NAME)
embeddings = OpenAIEmbeddings(base_url=BASE_URL, api_key=API_KEY, http_client=http_client, model=EMBED_MODEL_NAME)
```

## Knowledge Directory (`.knowledge/`)
| Node | Purpose |
|---|---|
| [state-progress.md](.knowledge/state-progress.md) | Current build state, what's done/next |
| [decisions-log.md](.knowledge/decisions-log.md) | Architecture/tech decisions + rationale |
| [errors-solved.md](.knowledge/errors-solved.md) | Bugs hit + fixes, so we never re-debug them |
| [env-network.md](.knowledge/env-network.md) | API keys, models, proxy/network quirks |
| [citations.md](.knowledge/citations.md) | Docs/links referenced during the build |

## SESSION START PROTOCOL
> **Any new AI session or teammate MUST read `.knowledge/state-progress.md` first**,
> before touching code. Then skim `decisions-log.md` and `errors-solved.md`.
> Update `state-progress.md` at the end of every work session.
