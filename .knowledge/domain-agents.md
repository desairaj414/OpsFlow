---
type: domain
title: Domain — Agent Chain & Orchestration
status: draft
updated: 2026-08-07
related: [arch-overview.md, api-contract.md, domain-workflows.md, domain-guardrails.md]
---

From PRD §3.4 and §5 Phase 3 build order. **Two levels only: Supervisor + specialists — do not add
a third level or let specialists call each other directly.**

## Agent chain, in demo-importance order (PRD §5 Phase 3)
1. **Supervisor** — dispatches, validates each typed result against schema before continuing, owns turn caps and termination conditions.
2. **Enrichment** — gathers evidence across MCP-exposed systems, attaches artifact IDs.
3. **Diagnosis (DeepSeek R1)** — root-cause hypothesis generation & ranking; a hypothesis with no cited artifact is suppressed at generation, never filtered after.
4. **Planner (DeepSeek V3)** — drafts a plan **only** from the approved runbook catalog (runbook-bounded action space, see [domain-guardrails.md](domain-guardrails.md)); free-text remediation can only be raised as a proposal-for-a-new-runbook, routed to a human.
5. **Verification** — the Fake Fix Detector; requires two independent signals (alert cleared AND underlying metric/health probe recovered and held through a stabilisation window). See [domain-guardrails.md](domain-guardrails.md).
6. **Sync** — writes the outcome back to every simulated system as one consistent record.
7. **Knowledge (+ Negative KB)** — captures the outcome; on rejection/failure, seeds the Negative KB scoped to CI class + failure signature.

## A2A handoff choice
Exactly one handoff in this chain travels over A2A (PRD §3.8). **Decide which one in Phase 3 and
record the choice here** — do not leave it ambiguous once decided (this line updates from `draft` once chosen).

## Termination & turn discipline (PRD §3.3)
Every agent: explicit termination condition + turn cap. Rationale: MAST's "unaware of termination
conditions" failure mode, and the ITBench finding that more turns did not reliably mean better
answers — dense incident signal can lead an agent to keep surfacing correlated symptoms past the
point of commitment.

## Contracts
Full JSON shape for the Supervisor↔specialist handoff and the Agent Card: [api-contract.md](api-contract.md).

## Do not re-decide
Two-level topology, no direct agent-to-agent calls, in-process typed contracts by default — all
fixed in [decisions-log.md](decisions-log.md). If a phase finds a reason to deviate, stop and ask
the human.
