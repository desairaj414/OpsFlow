---
type: Reference
title: Bias Mitigation
description: How each of 9 identified bias sources (retrieval, instrumentation, historical assignment, alert verbosity, severity anchoring, automation bias, accent/speech, image context, negative-KB overcorrection) is mitigated in code, not just named.
tags: [guardrails, bias, fairness]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: domain-guardrails
    resource: .knowledge/domain-guardrails.md
    title: Domain — Guardrails & Bias Mitigation
    last_modified: 2026-08-07
---

# Overview

Nine identified ways bias can enter the pipeline, each paired with a concrete mitigation — the last
four were self-identified by the team while building the voice/vision/negative-KB features, rather
than being generic checklist items.[^domain-guardrails]

# Table

| Bias | How it enters | Mitigation |
|---|---|---|
| Retrieval recency/frequency | RAG force-fits novel incidents to familiar root causes | Diversity-aware retrieval + an explicit "no strong precedent found" state |
| Instrumentation/documentation | Well-monitored services get higher-confidence diagnoses | Confidence scored relative to evidence available for that CI + a "low observability coverage" flag |
| Historical assignment | Routing to whoever historically closed similar tickets entrenches mis-routing | Route to role/queue, never a named individual; reason shown and editable |
| Alert-verbosity | Terse legacy alerts under-ranked vs rich modern ones | Every signal normalized into `MaintenanceSignal` before any model ranks it |
| Severity anchoring | Vendor-labelled priority anchors model judgement | Priority recomputed from CI criticality + blast radius + SLA; disagreement shown as a delta |
| Automation bias (reviewer) | A confident-looking plan gets rubber-stamped | Approval screen shows the strongest counter-hypothesis + evidence gaps; reason mandatory on reject/edit; near-100% approval rate is treated as a warning sign, not a success metric |
| Accent/speech-pattern | ASR is worse for non-native/atypical speech, so an accessibility feature becomes inaccessible | Command-scoped closed vocabulary (never free dictation); parsed intent shown for confirmation before executing; full keyboard parity — see [Voice Intake](/intake/voice-intake.md) |
| Image-context | Modern dashboards extract cleanly; terminal dumps/legacy UIs extract poorly | Extraction confidence surfaced; mandatory human confirmation before a signal enters a workflow — see [Vision Intake](/intake/vision-intake.md) |
| Negative-KB overcorrection | A remediation that failed once in one context gets blanket-suppressed everywhere | Entries scoped to `(ci_class, failure_signature)`, shown as a caution with reason, never a silent filter — see [Knowledge Agent](/agents/knowledge-agent.md) |

[^domain-guardrails]

[^domain-guardrails]: Domain — Guardrails & Bias Mitigation
