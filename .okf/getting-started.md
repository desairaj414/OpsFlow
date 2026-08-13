---
type: Guide
title: Getting Started with OpsFlow
description: What OpsFlow is, the request lifecycle for one incident, and where to read next in this bundle.
tags: [overview, onboarding]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: claude-md
    resource: /CLAUDE.md
    title: CLAUDE.md hub index
    last_modified: 2026-08-07
  - id: arch-overview
    resource: .knowledge/arch-overview.md
    title: Architecture Overview
    last_modified: 2026-08-07
---

# Overview

OpsFlow is a prototype "Cross-Stack Maintenance Control Plane" for IT Application Maintenance: a
coordinated multi-agent system that turns three classes of manual IT-ops toil — incident
resolution, patch management, performance tuning — into one auditable, guardrailed pipeline from
"signal received" to "ticket closed, CMDB updated, knowledge captured."[^claude-md] The prototype's
point is proving the *coordination*, not just wrapping a chatbot around a ticketing system.

# The request lifecycle, once, end to end

1. A signal arrives — a fault alert (primary path), a voice command, or a screenshot — and is
   normalized into one canonical `MaintenanceSignal` object, then scrubbed of PII/secrets. See
   [Intake](intake/).
2. The Supervisor dispatches a fixed chain of specialists: Enrichment gathers evidence, Diagnosis
   (the one step that travels over a real A2A handoff) generates cited root-cause hypotheses,
   Planner drafts a plan from retrieved runbook chunks and computes blast radius + a policy-gate
   decision. See [Agents](agents/) and [Guardrails](guardrails/).
3. If the policy gate requires it, a human approves or rejects (with a mandatory reason) before
   anything "executes." See [Workflows](workflows/) for how this differs across incident/patch/
   performance-tuning.
4. Verification's Fake Fix Detector checks two independent signals (alert cleared **and** the
   underlying metric held recovered) before calling anything genuinely fixed. Sync writes a
   consistent outcome back to the simulated ITSM/CMDB systems; Knowledge seeds a Negative KB entry
   if the fix turned out to be fake.
5. Every step logs an immutable audit entry. The Overview dashboard renders live metrics computed
   from that same data — see [Overview Metrics](architecture/overview-metrics.md).

# Where to read next

- New to the codebase? Start with [Tier Architecture](architecture/tier-architecture.md) for the
  system diagram, then [Agents](agents/) for the chain in demo-importance order.
- Working on the LLM layer? Read [Provider Registry](architecture/provider-registry.md) and
  [Provider Propagation](architecture/provider-propagation.md) — this is the part of the system
  most recently and substantially reworked (see below).
- Curious why a decision looks the way it does (two-level agent topology, one A2A handoff, no
  workflow checkpointing)? See [Decisions](decisions/).

# A system mid-refactor — read this before trusting "the old docs"

OpsFlow's own `.knowledge/` tree (this bundle's primary source) was written against an earlier
design where every LLM call went to one hardcoded TCS GenAI Lab endpoint. That has since been
replaced by a genuine multi-provider architecture — see
[Provider Registry](architecture/provider-registry.md) and
[Multi-Provider Architecture](decisions/multi-provider-architecture.md) — so that OpsFlow can run
as a public, self-serve demo instead of only on the TCS corporate network. Two `.knowledge/` files
in particular (`models-routing.md`, `arch-overview.md`) still describe the old single-endpoint
state in places; this bundle was written from the actual code (`backend/providers.py`,
`provider_context.py`) as the source of truth wherever the two disagree.

[^claude-md]: CLAUDE.md hub index
