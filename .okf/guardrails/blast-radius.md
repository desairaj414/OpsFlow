---
type: Module
title: Blast Radius
description: Deterministic BFS over the CMDB relationship adjacency graph, computing how many CIs a proposed action could plausibly affect. Feeds the policy gate's block/approval thresholds directly.
resource: backend/guardrails/blast_radius.py
tags: [guardrails, deterministic, cmdb]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: blast-radius-py
    resource: backend/guardrails/blast_radius.py
    title: backend/guardrails/blast_radius.py
    last_modified: 2026-08-11
---

# Overview

`compute_blast_radius(ci_id, relationships, max_depth=2)` runs a breadth-first search out to
`max_depth` hops over the CMDB relationship graph, returning the set of affected CI ids (never
including the starting CI) and their count. Relationships are treated as **undirected** for this
purpose — any recorded coupling (`depends_on`/`hosts`/`connects_to`/`replicates_to`) means an
action on one CI can plausibly ripple to the other, regardless of which direction the edge was
recorded in.[^blast-radius-py]

# Schema

| Field | Meaning |
|---|---|
| `ci_id` | the CI the action targets |
| `affected_ci_ids` | sorted list of CIs reachable within `max_depth` hops |
| `count` | `len(affected_ci_ids)` — the number the policy gate's thresholds compare against |
| `max_depth` | the hop limit used (default 2) |

# Consumers

[Planner Agent](/agents/planner-agent.md) computes this after the LLM drafts a plan, then feeds
`count` into [Policy Gate](policy-gate.md)'s `BLAST_RADIUS_APPROVAL`/`BLAST_RADIUS_BLOCK` rules.
Never delegated to the model — this is exactly the kind of graph computation the routing principle
(see [Model Routing](/architecture/model-routing.md)) reserves for deterministic code.

[^blast-radius-py]: backend/guardrails/blast_radius.py
