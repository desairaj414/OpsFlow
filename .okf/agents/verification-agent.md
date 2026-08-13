---
type: Module
title: Verification Agent — the Fake Fix Detector
description: Fully deterministic anti-reward-hacking check. Requires two independent signals — alert cleared AND the underlying metric held recovered through a stabilisation window — before trusting a fix as real.
resource: backend/agents/verification.py
tags: [agents, guardrails, verification]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: verification-py
    resource: backend/agents/verification.py
    title: backend/agents/verification.py
    last_modified: 2026-08-11
  - id: domain-guardrails
    resource: .knowledge/domain-guardrails.md
    title: Domain — Guardrails & Bias Mitigation
    last_modified: 2026-08-07
---

# Overview

`run_verification(incident_id, alert_cleared, metric_series, metric_key, baseline_threshold)`
checks whether the underlying metric series **held** under threshold through the tail 30% of the
series (`_held_through_stabilisation_window`) — not just one recovered data point. It is entirely
deterministic; there is no LLM call anywhere in this module.[^verification-py]

# Why this exists

An external IT-ops benchmark cited in the PRD found roughly 44% of "solved" mitigation problems in
that benchmark were actually a generic restart loop with no real fix — an alert that stops firing
is not the same evidence as a system that actually recovered.[^domain-guardrails] Verification
encodes that lesson as code: if only the alert cleared, without the metric holding recovered, the
outcome is `symptom_suppressed` and the incident is treated as unresolved, not trusted as fixed.

# Status outcomes

| Status | Condition |
|---|---|
| `verified_resolved` | alert cleared **and** metric held recovered through the stabilisation window |
| `symptom_suppressed` | alert cleared but the metric did **not** hold recovered |
| `not_yet_resolved` | alert never cleared |

# Consumers

[Sync Agent](sync-agent.md) only proposes a CMDB update on `verified_resolved`.
[Knowledge Agent](knowledge-agent.md) only seeds a Negative KB entry on `symptom_suppressed`. The
Overview dashboard's "Completed" tile counts execution regardless of this status (see
[Overview Metrics](/architecture/overview-metrics.md)) — deliberately not conflated with
"verified fixed."

[^verification-py]: backend/agents/verification.py
[^domain-guardrails]: Domain — Guardrails & Bias Mitigation
