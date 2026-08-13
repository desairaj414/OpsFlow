---
type: Module
title: Knowledge Agent
description: Only acts on a symptom_suppressed outcome — seeds a Negative KB entry scoped to (ci_class, failure_signature) so a remediation that failed once is remembered, never a blanket filter. Deterministic, no LLM.
resource: backend/agents/knowledge.py
tags: [agents, negative-kb]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: knowledge-py
    resource: backend/agents/knowledge.py
    title: backend/agents/knowledge.py
    last_modified: 2026-08-11
---

# Overview

`run_knowledge(incident_id, ci_class, verification_status, failure_signature, attempted_fix)` is a
no-op for every outcome except `symptom_suppressed` (see
[Verification Agent](verification-agent.md)). On that outcome it inserts a row into
`negative_kb_entries` scoped to `(ci_class, failure_signature)` — recording what was tried, and
that it failed to actually hold, so future planning can be warned about it.[^knowledge-py]

# Why scoped narrow

Deliberately scoped to CI class + failure signature, never a blanket "this fix never works" filter
— see [Bias Mitigation](/guardrails/bias-mitigation.md)'s "Negative-KB overcorrection" row. A
remediation that failed once in one context should not be silently suppressed everywhere.

[^knowledge-py]: backend/agents/knowledge.py
