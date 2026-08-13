---
type: Module
title: Diagnosis Agent
description: LLM-driven root-cause hypothesis generation and ranking, invoked over the one real A2A handoff, with hard citation enforcement — an uncited or out-of-bundle hypothesis is dropped before it is ever returned.
resource: backend/agents/diagnosis.py
tags: [agents, llm, citation]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: diagnosis-py
    resource: backend/agents/diagnosis.py
    title: backend/agents/diagnosis.py
    last_modified: 2026-08-11
---

# Overview

`run_diagnosis(incident_id, evidence)` prompts the active provider's `reasoning`-role model (see
[Provider Registry](/architecture/provider-registry.md)) with the evidence bundle (IDs + extracts
only) and asks for 2-4 ranked root-cause hypotheses as JSON. It is the one step in the whole chain
genuinely needing multi-step reasoning over conflicting evidence, and the one step invoked over
[A2A](a2a-handoff.md) instead of a plain in-process call.[^diagnosis-py]

# Citation enforcement

`_parse_and_filter()` drops any hypothesis whose `cited_artifact_ids` is empty, or which cites an
ID outside the actual evidence bundle passed in — functionally "suppressed at generation," never a
downstream filter applied after the fact. Surviving hypotheses are sorted by confidence,
descending.[^diagnosis-py]

# Retry and termination

Runs inside a `TurnTracker` loop (cap 3): a JSON-parse failure retries (consuming a turn) rather
than failing immediately, since a model occasionally wraps its JSON in markdown fences or similar —
handled defensively before falling back to `termination_reason = TERMINATION_CAP_EXCEEDED`. Calls
`llm.ainvoke()` (async), not the synchronous `.invoke()` — see
[No Workflow Checkpointing](/decisions/no-workflow-checkpointing.md)'s sibling bug in
[Planner](planner-agent.md) for why a sync call here would matter (it blocked uvicorn's whole event
loop for the length of this call).

# Consumers

[Supervisor](supervisor.md) takes `result["hypotheses"][0]` (the top-ranked hypothesis) as
[Planner](planner-agent.md)'s input; an empty hypothesis list stops the workflow with
`stopped`/`no_valid_hypotheses`.

[^diagnosis-py]: backend/agents/diagnosis.py
