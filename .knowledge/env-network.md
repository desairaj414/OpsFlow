---
type: env
title: Environment & Network
status: draft
updated: 2026-08-07
---

## Endpoint
- Base URL: `https://genailab.tcs.in`
- Auth: API key issued at event (see Participant Handbook)

## Models Available
<!-- Fill in from Participant Handbook once received -->
-

## Network / Proxy Notes
- Corporate network requires SSL verification bypass (`verify=False`) — see `CLAUDE.md`.
- `TIKTOKEN_CACHE_DIR` must point locally since HF/tiktoken downloads are blocked.
- Local `ollama` models (if any): run `ollama list` (see `backend/smoke_test.py`).

## Ports
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
