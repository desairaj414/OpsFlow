---
type: domain
title: Domain — Guardrails & Bias Mitigation
status: active
updated: 2026-08-07
related: [domain-agents.md, domain-workflows.md, schema-db.md]
---

From PRD §2.3 (four pillars) and §2.5 (bias table). These are graded, testable behaviours — build
them as code with unit tests, not as prompt instructions.

## The four pillars (PRD §2.3)
- **(a) Domain-specific guardrails:**
  - **Runbook-bounded action space** — agents may only propose steps in the approved runbook catalog; free-text remediation can only be raised as a proposal for a new runbook, routed to a human.
  - **Policy gate (pure Python, no LLM)** — change-freeze windows, prod vs non-prod, CI criticality, dependency blast radius above threshold, max concurrent changes, required-approver role. Deterministic, unit-tested, shown to the jury as code.
  - **Confidence floor with explicit abstain path** — below threshold, escalate and name the missing evidence. "I don't know, and here is what I'd need" is a first-class output, not a failure state.
  - **Fake Fix Detector (anti-reward-hacking verification)** — requires two independent signals: alert cleared **and** underlying metric/health probe recovered and held through a stabilisation window. If only the alert cleared: mark `symptom_suppressed, root cause unconfirmed` and keep the incident open. (ITBench: 44% of mitigation problems "solvable" by a generic pod-restart loop with no real fix.)
- **(b) Automated multi-step workflows** — see [domain-workflows.md](domain-workflows.md), 11 observable/attributable/replayable steps.
- **(c) Zero data leakage** — scrub-before-send at every model boundary, including after voice transcription/image extraction; reversible tokenisation; local-model routing for highest-sensitivity content; no raw payload persistence. See [domain-privacy.md](domain-privacy.md).
- **(d) Trust and transparency** — citations mandatory (a hypothesis without one is suppressed at generation), calibrated disclaimers on the artifact itself (not a page footer), reproducibility (temperature 0 for decision steps, Replay button), explicit "what I could not verify" block on every diagnosis.

## Chunking — implementation spec, not intention (PRD §6.4)
Retrieved runbook text can be an action taken against production — a chunk that drops a preceding
"only if X" condition is dangerous, not just lossy.
1. Split on structural boundaries only (headings, numbered steps, clause numbers) — never on a character/token count.
2. A numbered step is atomic; if it exceeds the size budget it stays whole and over-budget.
3. Heading path carried as metadata (e.g. `Runbook 14 › Rollback › Step 3`) so citations point at a step.
4. **Preamble inheritance** — prerequisites/warnings before a procedure attach to every step chunk in it. This is the rule that prevents the dangerous case above.
5. Tables and code blocks are never split.
6. PDFs: extract with structure preserved, apply the same rules; if structure can't be recovered, flag and exclude the document rather than naively splitting it.
7. Overlap only at section boundaries, carrying the heading forward.

**Verification (three layers, build this):**
- `scripts/assert_chunks.py` — **fails the build** if a chunk begins mid-step, a numbered list is split across chunks, a chunk lacks a heading path, or a code block is broken. Run at end of Phase 1 and again in Phase 5. **Built and passing 2026-08-07** (22 runbooks, 9 postmortems, trap case `RB-001.md` step 4 confirmed intact) — chunker itself lives in `backend/chunking.py`.
- Chunk Inspector UI screen — show chunk boundaries on a real document (demotes to a static screenshot if Phase 4 runs long, never dropped entirely).
- One deliberate trap runbook whose step 4 spans a page break — named test case, mention it in the walkthrough.

## Bias mitigation table (PRD §2.5 — lead with the last four rows, they were self-identified)
| Bias | How it enters | Mitigation |
|---|---|---|
| Retrieval recency/frequency | RAG force-fits novel incidents to familiar root causes | Diversity-aware (MMR-style) retrieval + explicit "no strong precedent found" state |
| Instrumentation/documentation | Well-monitored services get higher-confidence diagnoses; legacy under-instrumented systems deprioritised | Confidence scored relative to evidence available for that CI + "low observability coverage" flag |
| Historical assignment | Routing to who historically closed similar tickets entrenches mis-routing | Route to role/queue, never a named individual; reason shown and editable |
| Alert-verbosity | Terse legacy SNMP traps under-ranked vs rich modern alerts | Normalise every signal into the canonical schema before any model ranks it |
| Severity anchoring | Vendor-labelled "P1" anchors model judgement | Priority recomputed from CI criticality + blast radius + SLA; disagreement shown as a delta |
| Automation bias (reviewer) | Confident-looking plan gets rubber-stamped | Approval screen shows strongest counter-hypothesis + evidence gaps; mandatory reason on reject/edit; edit rate tracked, ~100% approval flagged as a warning sign |
| Accent/speech-pattern (new, from voice D1) | ASR worse for non-native/atypical speech — accessibility feature becomes inaccessible | Command-scoped closed vocabulary (not free dictation); parsed intent shown for confirmation before executing; keyboard parity |
| Image-context (new, from vision D1) | Modern dashboards extract cleanly; terminal dumps/legacy UIs extract poorly | Extraction confidence surfaced; mandatory human confirmation before a signal enters a workflow; low-confidence extraction marked unverified |
| Negative-KB overcorrection (new, from D5) | A remediation that failed once in one context gets blanket-suppressed | Entries scoped to CI class + failure signature; shown as a caution with reason, never a silent filter |

## Phase 2 prerequisites for Phase 3's verification agent — CONFIRMED IN PLACE (2026-08-07)
- **Policy gate** — `backend/guardrails/policy_gate.py`, pure Python, 12 unit tests green, covers
  freeze-window/prod-vs-non-prod/blast-radius/max-concurrent/approver-role/advisory-only-tuning.
- **Blast radius** — `backend/guardrails/blast_radius.py`, BFS over CMDB adjacency, 9 unit tests
  green against hand-built fixtures.
- **Audit trail** — `backend/orchestrator/audit.py`, append-only enforced by a real SQLite trigger
  (not just application discipline — a raw SQL UPDATE/DELETE is rejected by the DB itself).
- **Scrubber** — `backend/guardrails/scrubber.py`, measured precision/recall in [domain-privacy.md](domain-privacy.md).
The Fake Fix Detector itself (the two-signal alert-cleared + health-probe-recovered check) is NOT
yet built — it belongs to the Verification agent, Phase 3, which can now assume all of the above exist.

## Do not re-decide
These are resolved PRD decisions. Deviating (e.g. loosening the runbook-bounded action space, or
dropping the two-signal verification requirement) requires stopping and asking the human.
