---
type: domain
title: Domain — Agent Chain & Orchestration
status: active
updated: 2026-08-16
related: [arch-overview.md, api-contract.md, domain-workflows.md, domain-guardrails.md]
---

From PRD §3.4 and §5 Phase 3 build order. **Two levels only: Supervisor + specialists — do not add
a third level or let specialists call each other directly.**

## Agent chain, in demo-importance order (PRD §5 Phase 3) — BUILT 2026-08-07
1. **Supervisor** (`backend/orchestrator/supervisor.py`) — dispatches, re-validates each typed result against the `SpecialistResult` schema before continuing, owns turn caps (`orchestrator/limits.py`) and termination conditions.
2. **Enrichment** (`backend/agents/enrichment.py`) — gathers evidence across MCP-exposed systems + Chroma retrieval, attaches artifact IDs. Deterministic, no LLM.
3. **Diagnosis** (`backend/agents/diagnosis.py`, `api_client.get_llm(role="reasoning", ...)` — provider-dependent, only the legacy `tcs` provider resolves to DeepSeek R1, see models-routing.md, **the one A2A handoff** — see below) — root-cause hypothesis generation & ranking; a hypothesis with no cited artifact (or citing an artifact outside the evidence bundle) is dropped before ever being returned, functionally "suppressed at generation."
4. **Planner** (`backend/agents/planner.py`, `api_client.get_llm(role="structured", ...)` — provider-dependent, only the legacy `tcs` provider resolves to `gpt-4.1-nano` (DeepSeek V3's human-approved substitute, see models-routing.md)) — drafts a plan **only** from retrieved runbook chunks (runbook-bounded action space, [domain-guardrails.md](domain-guardrails.md)); a step citing a non-retrieved chunk is dropped. Blast radius + policy gate computed deterministically after the LLM drafts, never delegated to the model.
5. **Verification** (`backend/agents/verification.py`) — the Fake Fix Detector; requires two independent signals (alert cleared AND the metric series held recovered through the tail of the stabilisation window, not a single point). Deterministic, no LLM. See [domain-guardrails.md](domain-guardrails.md).
6. **Sync** (`backend/agents/sync.py`) — writes the outcome back to ITSM + CMDB (via MCP) as one consistent record. Deterministic.
7. **Knowledge (+ Negative KB)** (`backend/agents/knowledge.py`) — captures the outcome; on `symptom_suppressed`, seeds the Negative KB scoped to CI class + failure signature. Deterministic.

All 6 specialists + the Supervisor tested together end to end for all 3 workflow families
(`backend/tests/test_supervisor.py`) — happy path (verified_resolved), Fake Fix Detector catching
a real degradation (symptom_suppressed + Negative KB seeded), blast-radius block, and
tuning-never-auto-executes, all against real gateway calls and real generated data, not fixtures.

## A2A handoff choice
**DECIDED 2026-08-07: Supervisor -> Diagnosis.** Chosen as the most demo-prominent reasoning step.
Implemented in `backend/a2a/{agent_card.py,endpoint.py,client.py}` — a real HMAC-SHA256-signed
Agent Card (verifiable, not decorative; local-only secret, not asymmetric PKI — documented as a
hackathon-scope simplification in `agent_card.py`), served at `/.well-known/agent-card.json`,
invoked at `/invoke` (port 9010 in production; in-process ASGI transport for tests/dev, same
pattern as `mcp_wiring.py`). `orchestrator/supervisor.py` calls `invoke_diagnosis_via_a2a` instead
of calling the Diagnosis agent in-process — this is the one real handoff; every other agent
(Enrichment, Planner, Verification, Sync, Knowledge) is called in-process with the typed
`SpecialistResult` contract, per "one A2A handoff only" (decisions-log.md). 6/6 tests green
(signature validity, tampering detection, discovery, invocation) — `backend/tests/test_a2a.py`.

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
