---
type: log
title: Session Log — Human-Facing Work Journal
status: active
updated: 2026-08-16
related: [../state-progress.md, ../decisions-log.md, session-workflow.md]
---

Append-only, newest session on top. Different from `.okf/log.md` (portable knowledge-bundle
changelog, concept-scoped) and `decisions-log.md` (product decisions only) — this one is for your
own record: what happened in each working session, at a glance, without needing to trust chat
history across `/compact` cycles. **Exempt from the ~200-line node-split rule** (CLAUDE.md
maintenance protocol item 5) — this file is meant to grow indefinitely.

## How an entry gets built (read this before writing one)
Anchor on git, not memory — chat history survives `/compact` unreliably, commits don't.
- **Commit range**: the previous entry's `Up to commit:` hash → current `HEAD`. Get the exact list
  with `git log <prev_hash>..HEAD --oneline`. (The very first entry below had no previous hash to
  anchor from, so it was bootstrapped once from this project's Claude Code transcript JSONL — the
  timestamp on the session's first message — cross-checked against `git log --since=<that
  timestamp>`. That bootstrap is a one-time thing; every entry after it uses the hash checkpoint.)
- **Major vs minor**: Major = anything that changed product behavior, architecture, a decision, or
  fixed a real bug — the kind of thing that would also earn a `decisions-log.md`/`.okf/log.md`
  entry, or that you'd actually want to remember later. One bullet each. Minor = pure
  wording/formatting/housekeeping — roll up into a single line pointing at the commit(s), don't
  itemize every file touched.
- **Skip reverted-within-session noise** (e.g. a binary file that got touched then reverted before
  ever being committed) — no lasting value in recording it.
- **Open / follow-ups**: anything flagged but not resolved by session end, carried forward so the
  next session doesn't lose track. Once an item resolves — same session or a later one — **delete
  its bullet outright**, don't strike it through or annotate "RESOLVED" in place; if it's worth
  remembering that it happened, fold it into that entry's Major list as a normal completed item
  instead. Also clean up any other place in the same entry that referred to it as still-open. If
  the list ends up empty, write "None open as of this entry." rather than leaving the header bare.
- **Verified**: what was actually tested (build/test-suite/live-check results) — distinct from
  "written," matching this project's own honesty discipline (CLAUDE.md maintenance protocol item 1).

---

## Session 2 — 2026-08-17
**Up to commit:** `e10a23b` (per the two-commit close-out convention, this is the last "content"
commit — this entry's own session-end commit isn't listed in itself; it'll show up as the first
item in Session 3's git-log range instead)
**Commits this session (7):** `91fca13`, `9eac9b3`, `289b1fa`, `223bb0d`, `591c5de`, `52dc22d`,
`e10a23b`. `91fca13` is Session 1's own session-end commit (finalized its log, not new work this
session — it just happens to be the first item in this session's git-log range).

**Major:**
- Retired phase-based execution tracking entirely: deleted every `prd-phase-N.md` and
  `extra-credit.md`, replaced with plain ongoing-state tracking in `state-progress.md`/`CLAUDE.md`.
  Closed out Phase 5 for real as part of that triage: scenario library grew from 6 to 14 fixtures
  (10 named + 4 edge-case), a new eval harness (`backend/eval/harness.py`), a model-call cache
  wiring the long-unused `model_call_cache` table into Diagnosis/Planner, a legacy-UI screenshot
  fixture, 3 synthetic (Windows TTS) voice-sample placeholders with real recordings still owed and
  clearly labeled as such. 2 of the 6 originally-planned edge-case types were found already covered
  by the Phase 2 scrubber test suite — reused, not duplicated. Phase 6 reframed as
  `.knowledge/reference/future-plans.md` (per-item verdict on what's still worth doing post-pivot);
  Phase 7 was already superseded by the actively-maintained `README.md` — `289b1fa`.
- Fixed a real dead-code bug in `guardrails/policy_gate.py`: the `FREEZE_WINDOW`/
  `MAX_CONCURRENT_CHANGES` rules were fully built and unit-tested but never reachable
  (`planner.py` always passed an empty `PolicyContext()`). Wired for real, scoped to `patching`
  workflows only after wiring it universally immediately broke 4 incident/tuning tests (a demo
  blackout window in `change_calendar.json` is deliberately date-ranged to include "now") —
  `289b1fa` (code), decision entry appended in `e10a23b`.
- Corrected the Verascope/OpsFlow branding record across the whole knowledge tree: git-confirmed
  (`git log -S"Verascope"`) the rebrand was reverted the same day it was introduced, before the
  hackathon's own Final Submission — the app has never actually shipped as anything but OpsFlow.
  Fixed the one real shipped leftover (`theme.js`'s `localStorage` key name) — `289b1fa`.
- Found and deleted 3 genuinely unneeded/misplaced files: an internal PRD draft sitting in the
  app's live Knowledge Base RAG folder (not yet embedded, but would have leaked into chat retrieval
  on the next Chroma reindex), a 1.7MB accidentally-committed tiktoken cache (`backend/token/`,
  properly gitignored now), and an empty root `PRD_DRAFT.md` placeholder — `289b1fa`.
- Restructured `.knowledge/` from 25 flat files into `domain/`/`architecture/`/`reference/`
  subfolders (highest-frequency files — `state-progress.md`, `decisions-log.md`, `rules-*.md` —
  stayed top-level), moved `PRD_FINAL.md`/`PHASE0_FINDINGS.md` into `.knowledge/reference/` with
  clearer names, rewrote every cross-reference. Split `decisions-log.md` (385 lines) into the live
  file + `decisions-log-history.md`, and trimmed `state-progress.md`'s stale KNOWN ISSUES back into
  `state-progress-history.md` — `289b1fa`, `e10a23b`.
- Found and fixed two separate rounds of a self-inflicted doubled-relative-path bug in the
  restructuring's own reference-rewrite scripts (`../architecture/../architecture/...` in the first
  pass, bare `reference/reference/...` with no `../` prefix in files that stayed top-level in a
  second) — verified clean both times via a full-repo link-resolution walk plus a broad
  doubled-segment regex sweep, not just spot-checks — `223bb0d`, `e10a23b`.

**Minor:**
- Portable dev-server launch config for backend/frontend (repo-relative paths, `.nvmrc`) —
  `9eac9b3`.
- Documented the `DEFAULT_PROVIDER=openrouter` test-suite fallback in `backend/conftest.py` for
  when Gemini's free tier rate-limits mid-suite; live-verified the switch itself works, corrected
  the note after OpenRouter's own free tier hit a separate transient failure on the actual
  verification run (not a guaranteed fix) — `591c5de`.
- Fixed a stale `.knowledge/session-log.md` path reference in `session-workflow.md`'s copy-paste
  prompts, broken by the restructuring (plain inline-code text, not a markdown link, so the
  reference-rewrite script never touched it) — `52dc22d`.

**Open / follow-ups for next session:**
- Real recorded voice samples still owed (PRD §6.1/§6.3 require actual human speech; 3 synthetic
  TTS placeholders exist meanwhile, clearly labeled, in `data/voice_samples/`).

**Verified:** Backend suite 96 passed / 2 skipped, both after the `policy_gate.py` fix and again
after the full restructuring (the 4 recurring failures are `test_vision_path.py`/
`test_intake_adapter.py` hitting real Gemini/OpenRouter rate limits — confirmed via isolated
reruns and a `DEFAULT_PROVIDER=openrouter` retry, unrelated to any code touched this session).
Eval harness 14/14 twice consecutively, both before and after the `policy_gate.py` fix (with
`SCEN-04`/`SCEN-08`'s `expected` blocks corrected to the real observed `blocked` outcome, not
forced to pass). `.okf` bundle `okf:validate --strict` clean (36 concepts, 0 errors) after every
sync pass. Full-repo relative-markdown-link resolution (203 links) and doubled-path-segment
sweeps both clean as of the final check. `python -m compileall` clean on the full backend.

---

## Session 1 — 2026-08-10 to 2026-08-16
**Up to commit:** `8d0c87d` (per the two-commit close-out convention below, this is the last
"content" commit — this entry's own session-end commit isn't listed in itself; it'll show up as
the first item in Session 2's git-log range instead)
**Commits this session (17):** `bce4785`, `ba2ad42`, `3faf67d`, `613aa88`, `b6ca809`, `b7a8e6b`,
`046b1a6`, `32e286a`, `8a9dab6`, `bd2446d`, `81ebfe9`, `8039c3d`, `bc2d29e`, `ea246b7`, `1552566`,
`35d43a6`, `8d0c87d` — spanning commit timestamps 2026-08-13 22:47 to 2026-08-16. The session
itself started 2026-08-10 19:04 (per the Claude Code transcript's first message) — several days of
design/audit work happened before the first commit landed.

**Major:**
- Pivoted the app off a single hardcoded TCS GenAI Lab endpoint to a 6-provider LLM architecture
  (Gemini default, OpenRouter fallback, TCS retained as legacy/gated, plus OpenAI/Grok/custom for
  BYOK) — `bce4785`, `ba2ad42`, `3faf67d`. See `.okf/decisions/multi-provider-architecture.md`.
- Built the 3-mode public demo UX (Instant Demo / Bring Your Own Key / Free Demo Key) with a real
  login-screen mode selector and pregenerated demo outputs — `bce4785`.
- Produced the initial OKF v0.2 knowledge bundle at `.okf/` — `bce4785`.
- Chose and stood up hosting: Render-only (Web Service backend + static-exported frontend Site),
  not Vercel+Render — `ba2ad42`. Fixed two real deploy-breaking bugs found live: a Python version
  pin for a `pydantic-core` build failure (`b6ca809`), and Chroma embeddings being rebuilt (and
  rate-limited) on every deploy instead of committed as a static artifact (`b7a8e6b`, `046b1a6`).
- Set up the Render MCP server in Claude Code (local scope — project scope doesn't work with
  Render's OAuth, header-based API-key auth used instead) so Claude could manage the live deploy
  directly. Not a git commit — a tooling/environment change (`.claude.json`, local scope).
- Deleted and recreated the live Render services to get clean URLs (`opsflow-backend-k6xm` /
  `opsflow-frontend-fz2u` → `opsflowapp-backend` / `opsflowapp`, after a name collision on the
  original Blueprint-created names) — `bd2446d`. Confirmed the new services stayed Blueprint-linked
  (auto-sync on future pushes) via a real `blueprint_sync` deploy record, not assumed.
- Full mobile-responsive pass across every cockpit screen — Sidebar becomes a slide-in drawer,
  native `<select>`s replaced with custom dropdowns, the agent-chain flow stacks into full-width
  cards on mobile, floating panels (chat, notifications) reposition instead of running off-screen,
  a proactive backend wake-up ping + "waking up" banner added for Render free-tier cold starts —
  `81ebfe9`, `8039c3d`.
- Repo hygiene: dropped the dead Vite/React backup and stale scratch notebooks, migration-complete
  docs updated — `32e286a`, `8a9dab6`.
- 2026-08-16: full accuracy audit of `.knowledge/` + `.okf/` against current code (three parallel
  audits) found `.okf/` mostly current but `.knowledge/` significantly stale — still describing the
  pre-pivot single-endpoint design in ~11 files. Fixed all of it, backfilled `decisions-log.md`
  with the two decisions that had only ever lived in `.okf/` (multi-provider pivot, Render-only
  hosting), split `state-progress.md` back under its line budget — `bc2d29e`. Also fixed a real
  code bug the audit surfaced: `supervisor.py` hardcoded TCS model names into the Agent Trace's
  `model_used` field regardless of the session's actual active provider — it now reports the real
  answering model via a new `SpecialistResult.model_used` field — `ea246b7`.
- Added this journal (`session-log.md`) and the git-anchored checkpoint mechanism it uses —
  `1552566`. While building it, checked two assumptions directly instead of trusting recollection:
  confirmed Render's old pre-rename services are actually gone (`list_services`), and found the
  GitHub repo was still **private**, not public as assumed — an unauthenticated GitHub API request
  returned `404`, GitHub's signature for private, not missing (the repo demonstrably exists and
  Render deploys from it live) — `35d43a6`. Flagged this against the original session goal of a
  public resume link; the human then made it public and it was reconfirmed the same way
  (`private: false`, `visibility: public`, HTTP 200) — not a git commit, a GitHub repo-settings
  change.
- Switched this journal to a two-commit close-out pattern (commit everything else first, then
  session-log.md alone as a separate "session-end commit") after hitting the self-referential
  "Up to commit" problem three times in one session — `8d0c87d`. See this file's own header.
- Pushed all of this session's commits (through this entry's own eventual session-end commit) to
  `origin/main` after committing it — verified no divergence first via `git fetch` +
  `git log origin/main..HEAD`.

**Minor:**
- Theme toggle added to the login screen (post-login screens already had one) — `613aa88`.

**Open / follow-ups for next session:** None open as of this entry.

**Verified:** `.okf` bundle `okf:validate --strict` clean (34 concepts, 0 errors) both after the
docs sync and again after the `model_used` fix; backend suite 96 passed / 2 skipped (real gateway
calls — the 4 "errors" are `smoke_test.py`'s own script-style tests misfiring under bare `pytest`
collection, pre-existing and unrelated to this session's changes); `npm run build` clean for the
mobile-responsive pass; live Playwright verification against production
(`opsflowapp.onrender.com`) for the mobile UI fixes.
