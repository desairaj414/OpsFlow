---
type: Decision
title: One A2A Handoff, Not All Agent Traffic
description: Only Supervisor -> Diagnosis travels over the real A2A protocol; every other specialist call stays in-process with typed Python contracts.
tags: [architecture, a2a, protocol]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: decisions-log
    resource: .knowledge/decisions-log.md
    title: Decisions Log
    last_modified: 2026-08-07
---

# Decision

Exactly one Supervisor <-> specialist handoff (Diagnosis) travels over
[A2A](/agents/a2a-handoff.md), chosen as the most demo-prominent reasoning step. Every other
specialist (Enrichment, Planner, Verification, Sync, Knowledge) is called in-process with the
typed `SpecialistResult` contract.

# Alternatives considered

Routing all agent traffic over A2A, to make a stronger protocol-adoption claim.[^decisions-log]

# Rationale

The architectural claim being proven only needs one genuinely demonstrated handoff — a real,
verifiable signed Agent Card, real discovery, real invocation. Extending A2A to every specialist
call would be real implementation burden (a second Agent Card, a second endpoint, more surface for
transport failures) for no marginal credit toward that claim.[^decisions-log] Documented explicitly
as a scoped choice: if time runs out, the fallback plan was "cut the A2A implementation, keep the
argument" — i.e. it is acceptable to say the team designed for A2A and did not implement it, but
never acceptable to imply more was built than actually was.

[^decisions-log]: Decisions Log
