---
type: Reference
title: Model Routing — LLM vs SLM vs Classical ML vs Deterministic
description: The routing principle (route by task shape, not model prestige) and exactly which technique each pipeline step uses.
tags: [llm, architecture, routing]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: architecture-as-built
    resource: .knowledge/architecture-as-built.md
    title: Architecture As-Built
    last_modified: 2026-08-08
  - id: rules-backend
    resource: .knowledge/rules-backend.md
    title: Backend Rules & Commenting Standard
    last_modified: 2026-08-07
---

# The routing rule

Before writing any function that calls a model, ask: is this task deterministic? If yes
(correlation, policy checks, blast radius, voice-intent parsing, metric math, scheduling
constraints), it must be plain Python / scikit-learn — never an LLM call. Using an LLM for
arithmetic or rule evaluation is treated as a hard code-review failure here, not a style
preference.[^rules-backend]

# Technique per pipeline step

| Step | Technique |
|---|---|
| Correlate | Classical ML — scikit-learn DBSCAN over alert timestamps within CMDB-topology + category buckets |
| Enrich | Deterministic MCP tool calls + one real RAG/vector lookup (Chroma `ticket_history`) |
| Diagnose | LLM, `reasoning`-role model, over the one real A2A handoff |
| Plan | RAG (Chroma `runbooks`, scoped by class) + LLM `structured`-role model, then deterministic guardrails (blast radius, policy gate, and for patch workflows, scheduling) |
| Policy Gate | Deterministic rule engine (pure Python, no LLM, no ML) |
| Execute | Deterministic — audit-log write only, no real script execution against live infrastructure |
| Verify | Deterministic — the Fake Fix Detector, two independent signals required |
| Sync | Deterministic — writes back to ITSM + proposes a CMDB update |
| Knowledge | Deterministic — seeds the Negative KB on a suppressed-symptom outcome |
| Voice/image intake scrub | Local SLM (Ollama) + regex, never a hosted model |
| Voice intent parsing | Deterministic closed-vocabulary matcher — never an LLM, see [Voice Intake](/intake/voice-intake.md) |
| Any LLM call, if the active provider fails | Local Ollama SLM offline fallback |
| Chat assistant intent classification | LLM (`default`-role model); everything the classifier's intent triggers (ticket queries, approve/reject) is a real deterministic action, not model-generated |

This table describes technique per step, not which literal model id fills an LLM/SLM role for a
given provider — that mapping lives in [Provider Registry](provider-registry.md) (current,
multi-provider) since the original hackathon-era model-per-task table (`.knowledge/models-routing.md`)
was written against the single TCS endpoint and has not been kept in sync with the provider
refactor.[^architecture-as-built]

# Rehearsed trade-offs

- The reasoning-role call (Diagnosis) costs latency — tens of seconds on a busy provider; it runs
  on one step only, asynchronously.
- Higher agent turn counts are not reliably better (an external benchmarking finding cited in the
  PRD) — hence hard turn caps per agent, see [Supervisor](/agents/supervisor.md).
- Voice/vision latency is confined to intake, never the main agent loop.
- Local SLMs are weaker — used only for narrow tasks (redaction, classification), never for
  reasoning steps.

[^architecture-as-built]: Architecture As-Built
[^rules-backend]: Backend Rules & Commenting Standard
