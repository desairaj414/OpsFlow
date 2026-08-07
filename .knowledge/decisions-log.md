---
type: decision
title: Decisions Log
status: active
updated: 2026-08-07
related: [extra-credit.md, arch-overview.md, models-routing.md]
---

Pulled directly from `PRD_FINAL.md` §3.7, §4.0 and §4.3 (already-resolved decisions). One line
each: decision — alternative rejected — reason. **Do not re-litigate any of these.** If a phase
turns up a reason one should change, stop and tell the human; do not edit this log unilaterally.

## Log (from PRD §3.7 — alternatives considered)
- **Two-level Supervisor + specialists** — rejected: single do-everything agent, fully autonomous remediation, LLM-based correlation, off-the-shelf frameworks (LangGraph/CrewAI/AutoGen), routing all traffic over A2A, an MCP server that "coordinates agents". Reason: MAST data attributes 44.2%/32.3% of multi-agent failures to system design/misalignment; centralised validation bottleneck contains error amplification to ~4.4× vs ~17× uncoordinated.
- **Deterministic correlation (classical ML, CPU)**, not LLM-based — rejected: LLM event correlation. Reason: non-deterministic, expensive, unexplainable, worse than clustering at the task.
- **Closed-vocabulary deterministic voice intent parsing**, not LLM parsing or free-form dictation — rejected: LLM-based intent parsing, free-form voice dictation. Reason: a misheard command reaching an approval action is unacceptable; command-scope + on-screen confirmation is the safety choice.
- **MCP + A2A over an agent framework** — rejected: LangGraph/CrewAI/AutoGen. Reason: handbook rewards framework independence/explainability; MCP+A2A already provide the needed interop.
- **One A2A handoff only**, not routing all agent traffic over A2A — reason: the architectural claim needs exactly one demonstrated handoff; more is real implementation burden for no marginal credit.
- **Simulated ITSM/Tracker/Monitoring/CMDB (our own FastAPI)**, not real ServiceNow PDI — rejected: real ServiceNow PDI. Reason: hibernates ~24h, releases after 10 days, possible waitlist, licence framing, lab-network risk; simulators can also produce scenarios (50-alert storm, 6-month CMDB drift, planted credential) a real instance cannot produce on demand.
- **SQLite + Chroma**, not Postgres/Neo4j — reason: moderate data volume (hundreds of records); SQLite + an adjacency table covers CI relationships without overkill.
- **Structural chunking (heading/step boundaries)**, not fixed-size chunking — reason: naive fixed-size splitting can cut a runbook step mid-instruction, which is dangerous when the retrieved text is an action against production. See §6.4 / [domain-guardrails.md](domain-guardrails.md).

## Log (from PRD §4.0 — trade ledger, what was cut to fund voice/vision/full-parity tuning)
- **Cut scoped chat drawer** — reason: voice is now the conversational modality (D1), so the hybrid-interaction guidance is still satisfied without the "is this just a chatbot" framing risk.
- **A2A: three handoffs reduced to one** — reason: one handoff already proves the architectural claim.
- **Autonomy Ladder → status panel, not a live promotion engine** — reason: displaying the ladder makes the point; live promotion is a mid-term roadmap item (§2.7).
- **Maintenance Planner → a panel inside Incident Workspace, not its own screen** — reason: it was serving only one scenario.
- **Simulator field fidelity thinned to ~12 demo-relevant fields per system** — reason: authentic field *names* matter to jurors (`sys_id`, `fields.status.name`); full vendor data-model coverage does not.

## Log (from PRD §4.3 — explicitly not built)
- **No multilingual intake** — reason: the problem is machine-to-machine (alerts/CIs/logs/runbooks are English); inclusion effort was invested in accessibility (voice) instead.
- **No real ServiceNow PDI** — see rejection above.
- **No real script execution against live infrastructure** — reason: simulated execution with genuine state/metric movement is the honest, reproducible choice; never imply it is real infrastructure.
- **No ReAct-style open loops** — reason: "more turns made it worse" finding (ITBench); hard turn caps instead.
- **No real authentication** — reason: zero marginal credit, real cost. Role switcher is simulated identity, server-side enforced, stated as such.

## Template for any NEW decision made during execution
- **Decision:**
- **Alternatives considered:**
- **Rationale:**
- **Date:**
<!-- Append new decisions below this line, newest last -->
