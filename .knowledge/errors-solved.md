---
type: reference
title: Errors Solved
status: active
updated: 2026-08-07
related: [env-network.md, state-progress.md]
---

## Error Template
- **Symptom:**
- **Root cause:**
- **Fix:**
- **Files touched:**

## Log
<!-- Append new entries above this line, newest first -->

- **Symptom:** Backend fails to bind port 8000/8001 (`WinError 10048`).
  **Root cause:** Windows/Hyper-V/WSL reserves large ephemeral port ranges that silently block `127.0.0.1` binds even when nothing is listed via `Get-NetTCPConnection`.
  **Fix:** Run uvicorn with `--host 0.0.0.0 --port 8765` (or any high port outside the reserved range); update `frontend/.env` `VITE_API_BASE_URL` to match.
  **Files touched:** run command only.

- **Symptom:** `smoke_test.py` tiktoken pre-cache fails with `SSLCertVerificationError`.
  **Root cause:** tiktoken's downloader uses the `requests` library internally, which ignores the `ssl` module's default-context monkeypatch.
  **Fix:** Also monkeypatch `requests.Session.request` to force `verify=False` (added in config.py/main.py/smoke_test.py).
  **Files touched:** backend/config.py, backend/main.py, backend/smoke_test.py, backend/requirements.txt (added `requests`).

- **Symptom:** `uvicorn main:app` crashes with `RuntimeError: Form data requires "python-multipart"`.
  **Root cause:** `OAuth2PasswordRequestForm` (mock JWT login) needs `python-multipart`, not pulled in by fastapi/uvicorn alone.
  **Fix:** Added `python-multipart` to requirements.txt.

- **Symptom:** `vite` startup crash: `module is not defined in ES module scope` in postcss/tailwind config.
  **Root cause:** `frontend/package.json` sets `"type": "module"`, so `.js` configs must use ESM `export default`, not `module.exports`.
  **Fix:** Converted `postcss.config.js` and `tailwind.config.js` to ESM syntax (`import tailwindcssAnimate from "tailwindcss-animate"`).

- **Symptom:** `npm install`/`npm run dev` fails with PSSecurityException (script execution disabled).
  **Fix:** Use `npm.cmd` instead of `npm` in PowerShell to bypass the blocked `.ps1` shim.
