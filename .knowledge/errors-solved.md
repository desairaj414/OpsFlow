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

- **Symptom:** After adding a background "auto-diagnose newly-arrived alerts" watcher, an unrelated
  `fetch()` from the SAME browser tab (clicking "Open" on a ticket, `GET /tickets/{id}`) hung
  indefinitely — no response, no error, no timeout — even though the exact same endpoint answered
  a plain `curl` instantly. Confirmed with a raw `page.evaluate(() => fetch(...))` bypassing all app
  code: still hung. Not a frontend bug.
  **Root cause:** `agents/diagnosis.py` and `agents/planner.py` called `llm.invoke()` (synchronous)
  inside `async def` handlers — this blocks uvicorn's single-threaded event loop for the ENTIRE
  gateway round-trip (DeepSeek R1: "tens of seconds" even on a healthy gateway). While one request
  was mid-diagnosis, the backend genuinely could not service ANY other request, including totally
  unrelated ones, until that call returned. This was already flagged as a known architectural issue
  (see the offline-fallback entry in state-progress.md) but only became demonstrably serious once
  auto-triage started running real diagnosis calls continuously in the background — previously the
  blocking window was one-off (a single manual "Diagnose" click); now it recurs constantly.
  **Fix:** `llm.invoke(...)` → `await llm.ainvoke(...)` in both files — `ChatOpenAI` (and the
  `.with_fallbacks(...)`-wrapped runnable from the offline-fallback work) both support native async,
  no other code needed to change. Confirmed the hang is gone with the same raw-fetch test, and
  `tests/{test_diagnosis,test_planner,test_supervisor}.py` (14 tests) still pass.
  **Files touched:** `backend/agents/diagnosis.py`, `backend/agents/planner.py`.

- **Symptom:** `agents/planner.py`'s `where={"class": runbook_class}` Chroma query intermittently
  raised `RuntimeError: Cannot return the results in a contigious 2D array. Probably ef or M is too
  small` — non-reproducible in isolation at first (looked like gateway flakiness), then reproduced
  consistently for `tuning`/`performance`/`patching` runbook classes after the Knowledge Base tab's
  20 new chunks were added to the same collection.
  **Root cause:** the `"runbooks"` Chroma collection was created with no `hnsw:search_ef` metadata,
  so hnswlib used its small default. A `where`-filtered query first collects every candidate id
  matching the filter (here, every chunk from every runbook of that class), then asks hnswlib for
  `k` = that candidate count — once the collection grew past ~68 matching candidates for some
  classes, `k` exceeded the default `search_ef`, which hnswlib can't satisfy.
  **Fix:** `collection.modify(metadata={"hnsw:search_ef": 500})` on the existing collection (query-
  time param, changeable without re-indexing); baked `metadata={"hnsw:search_ef": 500}` into every
  `get_or_create_collection("runbooks", ...)` call site so a future from-scratch rebuild doesn't
  reintroduce it.
  **Files touched:** `backend/db/load_chroma.py`, `backend/main.py` (both `get_or_create_collection`
  calls).

- **Symptom:** After editing `main.py` and restarting `uvicorn`, `curl`/browser requests kept
  returning the OLD pre-edit behavior (missing new response fields) even though the new `uvicorn`
  process logged "Application startup complete." with no errors.
  **Root cause:** A stale backend process from an earlier session was already bound to port 8765.
  The new `uvicorn` invocation silently failed to bind (`[WinError 10048] only one usage of each
  socket address...`) and exited, while the old process kept serving unedited code on the same port.
  **Fix:** `netstat -ano | grep ":8765"` to find the real LISTENING pid, kill it, then start `uvicorn`
  fresh. Always confirm the *new* process is the one actually bound before trusting a "no errors"
  restart, especially on Windows.
  **Files touched:** none (operational, not a code bug).

- **Symptom:** `GET /alerts/stream` (SSE) returned an incomplete/truncated response
  (`ERR_INCOMPLETE_CHUNKED_ENCODING` in the browser console) instead of the live alert feed.
  **Root cause:** A new `LEFT JOIN cmdb_ci ON cmdb_ci.id = alerts.ci_id` added an `id` column to the
  `SELECT` without qualifying it — both `alerts` and `cmdb_ci` have an `id` column, so SQLite raised
  `ambiguous column name: id` inside the async generator, killing the stream mid-response.
  **Fix:** qualify as `alerts.id` in the column list whenever a query joins two tables that both have
  an `id` column.
  **Files touched:** `backend/main.py` (`_fetch_alerts_after`).

- **Symptom:** `POST /intake/confirm` returned HTTP 400 with a cryptic message: `Expecting ','
  delimiter: line 1 column 175 (char 174)` — looked like a client-input validation failure but the
  same request succeeded on immediate retry.
  **Root cause:** `json.JSONDecodeError` is a `ValueError` subclass. A transient gateway hiccup deep
  in the agent chain (likely the runbook-retrieval embeddings call) raised one, and
  `main.py`'s `except ValueError as e: raise HTTPException(400, str(e))` around
  `start_workflow_from_confirmed_signal` caught it indiscriminately alongside the two *intentional*
  validation errors that function raises (unconfirmed signal, no resolvable CI ref) — mislabeling a
  transient upstream failure as a permanent 400.
  **Fix:** narrowed the handler to 400 only on the two known validation messages; everything else
  (including nested `JSONDecodeError`) now returns 502 with "likely transient — try again".
  **Files touched:** `backend/main.py`.

- **Symptom:** React console error — `Encountered two children with the same key, 'CI-0006'` in
  `IncidentWorkspace.jsx`'s evidence list.
  **Root cause:** `key={e.artifact_id}` assumed `artifact_id` is unique per evidence entry, but
  `agents/enrichment.py` gives both the CMDB-fact and CMDB-relationship entries the same
  `artifact_id` (the CI itself) — they only differ by `source_type`.
  **Fix:** compound key `${artifact_id}-${source_type}-${index}`.
  **Files touched:** `frontend/src/components/IncidentWorkspace.jsx`.

- **Symptom:** Real browser `MediaRecorder` voice recordings would likely fail Whisper transcription
  (caught in self-review, not actually reproduced with a real failure).
  **Root cause:** `intake/voice_path.py`'s `_transcribe` hardcoded the multipart upload filename as
  `"voice.wav"` regardless of actual audio format; Whisper infers format from the filename
  extension, and browser `MediaRecorder` output is WebM/Opus, not WAV. The existing test used
  synthetic WAV bytes, so it never exercised this mismatch.
  **Fix:** added a real `filename` param to `run_voice_intake`/`_transcribe` (default unchanged,
  backward compatible), threaded through from `main.py`'s `POST /intake/voice` using the browser's
  actual `file.filename`.
  **Files touched:** `backend/intake/voice_path.py`, `backend/main.py`.

- **Symptom:** `test_scrubber.py::test_scrubbed_text_never_contains_original_secret_values` failed — a planted phone number `(338)393-4887` survived scrubbing.
  **Root cause:** the phone regex in `guardrails/scrubber.py` required a literal separator (`[-.\s]`) between the area-code parens and the next digit group; `(338)393-4887` has no character there, only some Faker-generated formats do.
  **Fix:** made both inter-group separators optional (`\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}`) — deliberately erring toward over-matching, since over-redaction is the safer failure mode for a scrubber than under-redaction.
  **Files touched:** `backend/guardrails/scrubber.py`.

- **Symptom:** `mcp.server.fastmcp` — `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` despite `mcp` being installed.
  **Root cause:** `mcp==1.1.2` (the version originally pinned) predates `FastMCP`, which was added in a later 1.x release.
  **Fix:** bumped to `mcp==1.9.4` (a later stable 1.x release, not the untested 2.0.0 major).
  **Files touched:** `backend/requirements.txt`.

- **Symptom:** `pip install -r requirements.txt` fails: `ResolutionImpossible` — `langchain==0.3.7` vs `numpy==2.1.3`.
  **Root cause:** `langchain 0.3.7` pins `numpy<2.0.0` on Python 3.12; `numpy==2.1.3` was requested for the Phase 1 data-gen additions.
  **Fix:** pinned `numpy==1.26.4` instead.
  **Files touched:** `backend/requirements.txt`.

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
