---
type: reference
title: Future Plans — Post-Cleanup Backlog
status: active
updated: 2026-08-17
related: [../decisions-log.md, ../state-progress.md]
---

Replaces `prd-phase-6.md`/`extra-credit.md` (deleted as part of the phase-logic cleanup — see
`decisions-log.md`'s newest entry). Phase 6 was framed as "extra credit for judges," conditional on
a Phase 5 gate closing before a hackathon submission deadline. That deadline has already passed
(commit `6299a26`, "Final Submission") and the app is now a hosted public portfolio piece, not a
judged demo — so every item below is re-evaluated against **that** context, not the original one.
Nothing here is built; this is a scoped backlog for if/when you want to pick one up.

## From the original Phase 6 / extra-credit list

| Item | Original scope | Still worth it? | Why / what changed |
|---|---|---|---|
| HTML quick-view launcher (`demo.html`) | Static page, buttons to jump to each scenario/screen | **No** | Solved navigation fumbling on a judge's laptop during a live pitch. The app is a real hosted Next.js cockpit with its own nav and a Scenario Launcher panel (`ScenarioLauncherPanel.jsx`) — a second, separate static launcher would be a duplicate, worse UI. |
| Real-Jira portability wiring | Show an agent-created ticket in actual Jira, if the Phase 0 probe succeeded | **No, as originally scoped** | Was a 30-second "look, it's real Jira" demo beat for a judge. `integration_settings` (the ServiceNow/Jira config table/panel) already exists as a stated-but-simulated integration point — if you ever want a real outbound integration, that's the extension point, but building it purely to replay a hackathon demo beat has no audience now. |
| Self-consistency on root-cause ranking | Sample N times, keep recurring hypotheses, report agreement rate | **Maybe, small** | Diagnosis already runs at temperature=0 for reproducibility (by design — same input, same output, no sampling variance to measure). Doing this meaningfully would mean deliberately raising temperature for an eval-only side-path, which cuts against the reproducibility decision already made. Real value only if you want a credibility metric ("hypotheses are stable across N samples") for a portfolio write-up — cheap enough (`backend/eval/harness.py` could add a `--repeat N` mode) if that's ever wanted. |
| Prompt-injection resilience beat | Surface the §6.2 adversarial log line as a named demo moment | **Already done, differently** | The scrubber's prompt-injection detection is built and measured (`domain-privacy.md`: "Adversarial prompt-injection line: flagged correctly (1/1), zero false positives") — via `pii_ground_truth.json` + `guardrails/scrubber.py`'s own test suite, not a scenario fixture. Nothing to add except maybe surfacing this specific measured result somewhere in the UI (e.g. a line in the Overview eval-status footer) if you want it visible to a visitor, not just in the knowledge base. |
| Notification connectivity | Approvals/summaries pushed to a simulated channel (Slack/Teams-shaped) | **Maybe** | A notification bell already exists (`NotificationBell.jsx`) but it's for *new alert arrivals*, not outbound approval/summary notifications to an external-shaped channel. If you want "here's what happened while you were away" as a real feature (not a judge-demo beat), this is a genuinely different, still-unbuilt capability — a small MCP-style simulated notification sink + a call from the approval path, mirroring how `itsm_mcp`/`tracker_mcp` are simulated today. |
| Change-risk classifier | CPU-trained tabular model over synthetic change history | **Maybe, if you want an ML component** | Nothing today does this — policy_gate.py is pure rule-based (deliberately, per `decisions-log.md` — "Deterministic correlation... not LLM-based"). A small classifier (e.g. logistic regression / gradient-boosted trees over `local_tickets`/`patch_inventory` history) trained offline and called deterministically at plan time would be a genuinely new capability, not a duplicate of anything existing. Real effort: data labeling (what counts as a "risky" past change?), training script, a call site in `planner.py`, a UI surface for the score. Medium-sized, not a quick add.
| Shift Handover Brief | One-click summary: open incidents, agent actions, pending approvals, refusals + reasons | **Partially overlaps with something that already exists** | `local_tickets` + the Ops Board's status filter + Ticket History already let someone see "what's open, what's pending approval" interactively. What's missing is the *one-click generated summary* framing (a single narrative brief, not a table someone has to read). If wanted: a new `GET /handover-brief` endpoint aggregating the same data `Overview.jsx`/`OpsBoard.jsx` already query, formatted as a short narrative (could reuse the existing "structured"-role LLM call pattern, or stay fully deterministic like the rest of the reporting surface). Small-to-medium. |
| Full eval harness | Per-scenario accuracy, citation coverage, hallucination checks | **Done** (this cleanup pass) | `backend/eval/harness.py` — see `state-progress.md`. Not "extra credit" anymore, it's built and wired into `/metrics/summary`. |
| Cost-per-incident meter | Unit economics against a stated engineer-hour cost | **Yes, cheap and still relevant** | Nothing today computes this. `audit_log`/`local_tickets` already have enough (timestamps, token counts via `SpecialistResult.tokens_used`, a stated $/token rate for whichever provider is active) to compute a real "$X model cost + Y minutes saved vs. a stated engineer-hour rate" tile. Small: one aggregation query + one Overview KPI tile, same shape as the existing timing tiles. Good candidate if you want one more concrete, cheap portfolio-credibility number. |

## New ideas (not in the original PRD, surfaced during this cleanup pass)

- ~~**Wire the dead freeze-window / max-concurrent-changes policy rules.**~~ **DONE 2026-08-17.**
  `agents/planner.py`'s `_load_policy_context()` now builds a real `PolicyContext`:
  `active_changes_in_environment` from a live COUNT against `local_tickets` (scoped to
  `status_normalized='needs_approval'`, the one status that's exclusively live-run-set, never
  present in bulk-seeded history); `freeze_windows` from the same `patch_mcp.get_change_calendar()`
  call Patch Management's maintenance-window logic already makes, **scoped to `patching` workflows
  only** — wiring it to every workflow type immediately broke incident/tuning tests, since
  `change_calendar.json`'s global blackout window is deliberately date-ranged to include "now" for
  the Patch Management demo, and blocking incident remediation on an unrelated code freeze isn't
  correct behavior. See `state-progress.md`'s LAST VERIFIED STEP for the full record.
- **Surface the scrubber's measured precision/recall in the UI**, not just `domain-privacy.md`. A small "privacy scrubber, proven" stat (already half-built as the `PiiScrubbingDemoCard` in `ScenarioLauncherPanel.jsx`, Instant-Demo-only) could pull the real numbers (100%/100%, 31 planted items) instead of just showing one example — cheap, reuses existing data.
- **A second BYOK/Free-Key eval mode for the harness** — right now `eval/harness.py` always runs against whichever provider is configured server-side. A `--provider` flag exercising the same 14 scenarios against Gemini vs. OpenRouter vs. TCS would give a real cross-provider consistency number, relevant now that the app is explicitly multi-provider (unlike the original single-TCS-endpoint PRD this eval concept was designed under).

## Not revisiting (still correctly out of scope)
Multilingual intake, real ServiceNow PDI, real script execution against live infrastructure, ReAct-
style open loops — the original PRD §4.3 reasoning for skipping these hasn't changed with the
multi-provider/hosting pivot. See `decisions-log.md`.
