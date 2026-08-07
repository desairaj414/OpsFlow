---
type: phase
title: "Phase 3 — Agent Chain, Supervisor, A2A & Multimodal Intake"
status: draft
updated: 2026-08-07
related: [domain-agents.md, domain-workflows.md, domain-multimodal-intake.md, api-contract.md, arch-overview.md, prd-phase-4.md]
---

**Duration ~5h · H+6:30–11:30 · Fri 15:30–20:30.** Two parallel tracks, same wall-clock window.
Gate for this phase = the **DEMO-COMPLETE CHECKPOINT** (H+11:30, Fri 20:30, ~66% through the full plan).

Owners: **Person D — Agents/Orchestration** · **Person E — Multimodal Intake + A2A.**

## Atomic steps — Track D (Agents/Orchestration, ~3h)
1. *(45 min)* Supervisor: dispatch loop + schema validation of each specialist's typed result before continuing. Files: `backend/orchestrator/supervisor.py`.
2. *(20 min)* Turn caps + explicit termination conditions per agent (PRD §3.3 "more turns ≠ better"). Files: `backend/orchestrator/limits.py`.
3. *(45 min)* Declarative workflow YAML for **incident** (build first) — the reference chain Correlate→Enrich→Diagnose→Plan→Gate→Approve→Execute→Verify→Sync→Learn. Files: `backend/orchestrator/workflows/incident.yaml`.
4. *(30 min)* Derive **patch** and **performance** workflow YAML from the incident one (PRD B9 — if this isn't nearly free, escalate immediately, the design assumption was wrong). Files: `backend/orchestrator/workflows/{patch,performance}.yaml`.
5. *(30 min)* Enrichment agent — gathers evidence via MCP tools, attaches artifact IDs. Files: `backend/agents/enrichment.py`.
6. *(35 min)* Diagnosis agent (DeepSeek R1) — hypothesis generation/ranking, citation enforcement built in from the start (a hypothesis with no cited artifact is suppressed at generation). Files: `backend/agents/diagnosis.py`.
7. *(20 min)* Planner agent (DeepSeek V3) — runbook-bounded plan drafting. Files: `backend/agents/planner.py`.
8. *(20 min)* Verification agent — Fake Fix Detector, two-signal check per [domain-guardrails.md](domain-guardrails.md). Files: `backend/agents/verification.py`.
9. *(15 min)* Sync + Knowledge(+Negative KB) agents. Files: `backend/agents/{sync,knowledge}.py`.

## Atomic steps — Track E (Multimodal + A2A, ~2.5h)
10. *(40 min)* Whisper voice path: audio → transcription → scrubber → intent parser (Phase 2) → confirmation-before-action → `MaintenanceSignal`. Files: `backend/intake/voice_path.py`.
11. *(40 min)* Llama Vision image path: image → extraction → scrubber → confirmation-before-action → `MaintenanceSignal` with `IMG-nnn` citation. Files: `backend/intake/vision_path.py`.
12. *(45 min)* A2A: pick exactly one Supervisor↔specialist handoff (record the choice in [domain-agents.md](domain-agents.md)), build the real signed Agent Card + endpoint. Files: `backend/a2a/agent_card.py`, `backend/a2a/endpoint.py`.
13. *(25 min)* Wire both intake paths + the A2A handoff into the Supervisor's dispatch loop; confirm scrubber runs after modality conversion, before any model call, on both paths.

## [MOCK-P1] markers
- Voice/image intake use real Whisper/Llama Vision gateway calls — not mocked, these are blocking Phase 0 checks.
- A2A endpoint runs locally, calls nothing outbound — label this in code comments per PRD §0 pre-empt language.

## Hard acceptance criteria (re-verify, don't just write) — this is the DEMO-COMPLETE gate
- [ ] One scenario from each of the 3 workflow families (incident/patch/performance) runs end to end through the full agent chain
- [ ] One signal enters via voice, confirmed on screen before the action executes
- [ ] One signal enters via a pasted/uploaded image, confirmed on screen before entering a workflow, cited as `IMG-nnn` downstream
- [ ] Exactly one handoff demonstrably travels over A2A with a viewable signed Agent Card
- [ ] Every hypothesis in the Diagnosis agent's output carries at least one cited artifact ID; none with zero citations reach the Planner
- [ ] Verification agent correctly distinguishes `verified_resolved` vs `symptom_suppressed` on at least one deliberately-rigged "alert cleared but root cause unconfirmed" fixture
- [ ] Turn caps enforced — an agent forced past its cap terminates with an explicit reason, not silently

## CONTEXT CHECKPOINT — update on completion
- [.knowledge/domain-agents.md](domain-agents.md) — record which handoff was chosen for A2A
- [.knowledge/state-progress.md](state-progress.md) — CURRENT PHASE → Phase 4, note DEMO-COMPLETE CHECKPOINT reached, DONE list
- [.knowledge/api-contract.md](api-contract.md) — record final Agent Card fields as actually implemented
- [.knowledge/domain-workflows.md](domain-workflows.md) — confirm patch/performance derivation cost matched the "nearly free" assumption; flag if not
