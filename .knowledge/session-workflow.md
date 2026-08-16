---
type: process
title: Session Workflow — Close-out & Start-up Prompts
status: active
updated: 2026-08-16
related: [state-progress.md, decisions-log.md, session-log.md]
---

Two reusable prompts for splitting long working threads into fresh sessions without losing
context or letting `.knowledge/`/`.okf/` drift out of sync with the code. Written after a
2026-08-16 audit found several `.knowledge/` nodes (arch-overview.md, architecture-as-built.md,
models-routing.md, rules-frontend.md, env-network.md, glossary.md, schema-db.md, api-contract.md,
domain-agents.md, domain-multimodal-intake.md, domain-workflows.md) had drifted stale relative to
the post-submission multi-provider/hosting pivot — none of it was caught until asked for directly.
Paste these verbatim; don't paraphrase from memory, since the value is in the checklist being
complete every time.

## Prompt A — run before ending a session

```
Before we close this session: review everything we changed today (git log/diff since the last
commit that touched .knowledge/ or .okf/), then bring .knowledge/ and .okf/ back in sync with
reality — don't just check the files you personally edited this session, spot-check a few nearby
concepts too, since staleness compounds silently between sessions. Specifically:
1. For any step a human has verified worked, add/update the relevant entry in
   .knowledge/state-progress.md (only verified steps — "written" and "verified" are different
   states, per CLAUDE.md's maintenance protocol rule 1).
2. For any new product/architecture decision made today, append it to
   .knowledge/decisions-log.md's template section (never edit existing entries).
3. For any change that affects a concept .okf/ already documents (new/removed module, changed
   provider/routing behavior, a new endpoint, a schema change), update that .okf concept's body +
   generated.at, fix cross-links, and append a dated entry to .okf/log.md.
4. Run the okf skill's validate mode (okf:validate --strict .okf) and fix every error.
5. Check whether any touched .knowledge/ node now exceeds ~200 lines and split it if so (topic
   files, update CLAUDE.md's index and any related: frontmatter pointing at the old node).
6. Commit everything from steps 1-5 now — EVERYTHING except .knowledge/session-log.md itself. This
   is the "content commit." (If you're about to push, do that fetch/divergence-check/push here too,
   for this commit — session-log.md's own commit in step 7 can go up in the same push right after.)
7. Only now, append an entry to .knowledge/session-log.md for this session, and commit it ALONE, as
   a second, separate "session-end commit." Get the exact commit range with
   git log <previous entry's "Up to commit" hash>..HEAD --oneline (this now includes the content
   commit from step 6) — don't guess from memory or dates. Classify each commit as major
   (product/architecture/decision/bugfix — one bullet each, named commit hash) or minor
   (housekeeping/wording — one rolled-up line covering all of them). Skip anything reverted within
   this same session before ever being committed. Carry forward any still-open items from the
   previous entry's "Open / follow-ups" (per session-log.md's own header instructions: delete
   resolved ones outright, don't strike them through). Add a "Verified" line: what was actually
   tested, not just written. Set "Up to commit" to the step-6 content commit's hash — NOT this
   session-end commit's own hash, which doesn't exist yet when you're writing its content and can't
   self-reference. That one-commit lag is expected and fine: the next session's git log range will
   start with this session-end commit itself: describe it there as "finalized session N's log," not
   as new substantive work. This file is exempt from the 200-line split rule — don't split it,
   don't trim old entries.
Use targeted edits only, never full-file rewrites — these are shared long-lived documents. When
done, give me a short summary of what you updated (file list, one line each) and confirm the
working tree is clean, or tell me exactly what's still uncommitted, before I end the session.
```

## Prompt B — run to start the next session

```
Resume work on OpsFlow (c:\Raj\OpsFlow). Read CLAUDE.md's hub index, then follow its "Read first,
every session" list (state-progress.md, decisions-log.md) — don't pre-read the whole .knowledge/
tree. Also skim .okf/log.md's most recent dated entries: the post-hackathon era (multi-provider
LLM pivot, 3-mode public demo UX, Render hosting, the OKF bundle itself, the mobile-responsive UI
pass) is tracked there and in decisions-log.md, not narrated in state-progress.md — see that file's
"POST-SUBMISSION WORK" note for why. Check for anything logged after your own last known date that
you haven't accounted for yet. Once synced, tell me so and ask what I want to work on — don't start
executing anything until I've told you the actual task. Before that, also skim the most recent
entry in .knowledge/session-log.md — its "Open / follow-ups" section is exactly the stuff that got
flagged but not finished last time (e.g. "committed but not pushed"), and its "Up to commit" hash
is what Prompt A will anchor the next close-out entry to.
```

## Why two prompts, not one

Close-out (A) writes; start-up (B) only reads. Running A at the end of every session is what keeps
B cheap — B assumes the tree is already accurate and just orients a fresh session against it,
rather than re-auditing from scratch every time. If A gets skipped for a few sessions in a row,
run a manual accuracy audit (compare `.okf/` + `.knowledge/` claims against current source, one
subagent per doc cluster) before trusting B's summary again — that's what surfaced the 2026-08-16
drift in the first place.
