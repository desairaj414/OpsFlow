---
type: phase
title: "Phase 1 — Data, Simulated Systems & MCP Layer"
status: draft
updated: 2026-08-07
related: [schema-db.md, api-contract.md, domain-guardrails.md, citations.md, prd-phase-2.md]
---

**Duration ~3h · H+1:30–4:30 · Fri 10:30–13:30.**
This is where the simulators are built — not later integration work. Every canonical schema, MCP
server, and agent contract descends from them. **Canonical schemas freeze at the end of this
phase** — after freezing, [api-contract.md](api-contract.md) and [schema-db.md](schema-db.md) flip `status: active`.

Owners: **Person A — Synthetic Data** (parallel track) · **Person B — Simulators + MCP servers,
owns this area for the whole event** (per PRD §5 — they answer "how faithful is this to the real API?" on stage).

## Atomic steps
1. *(45 min, Person A)* Generate CMDB (~200 CIs) + CMDB ground truth (~35% deliberately diverged), failed-remediation seeds (~40). Files: `backend/data_gen/cmdb.py`, `data/cmdb.json`, `data/cmdb_ground_truth.json`, `data/failed_remediations.json`.
2. *(45 min, Person A)* Generate alert stream (~500, heterogeneous shapes: Prometheus-like/SNMP-terse/APM-verbose), metric series CSVs (incl. slow-degradation curves for tuning), ticket history (400-600), change calendar, patch inventory. Files: `backend/data_gen/{alerts,metrics,tickets}.py`, `data/*.json|csv`.
3. *(30 min, Person A)* Write 18-22 runbooks (3 classes: `remediation`/`patching`/`tuning`, numbered clause-structured, declared human-step counts) + 8-10 postmortems, incl. the deliberate page-break chunking trap (PRD §6.4). Files: `data/runbooks/*.md`, `data/postmortems/*.md`.
4. *(45 min, Person B)* Build 4 thin-but-authentic FastAPI simulators (Monitoring, ITSM, Tracker, CMDB), ~12 demo-relevant fields each, real field names (`sys_id`, `fields.status.name`). [MOCK-P1] — these ARE the "external systems", labelled as simulators in the UI, never presented as real SaaS. Files: `backend/mcp_servers/simulators/{monitoring,itsm,tracker,cmdb}.py`.
5. *(45 min, Person B)* Wrap each simulator with a local MCP server exposing the typed tool set from [api-contract.md](api-contract.md) MCP section. Files: `backend/mcp_servers/{monitoring,itsm,tracker,cmdb}_mcp.py`.
6. *(30 min, either)* Freeze canonical schemas — `MaintenanceSignal`, DB tables — write final version into [api-contract.md](api-contract.md) and [schema-db.md](schema-db.md), flip both to `status: active`. **Do not skip this — every later phase pastes these in.**
7. *(30 min, either)* Populate SQLite (all tables from `schema-db.md`) + Chroma (`runbooks`, `postmortems`, `ticket_history`) with generated data.
8. *(30 min, either)* Build the chunker per [domain-guardrails.md](domain-guardrails.md) chunking rules + `scripts/assert_chunks.py`; get it passing against the runbook corpus, including the deliberate trap case.
9. *(15 min, either)* Gate script: an agent-free Python script drives one full scenario through the MCP tools end to end (no agents yet).

## Files created/modified
`backend/data_gen/*.py`, `data/*` (json/csv/md), `backend/mcp_servers/simulators/*.py`,
`backend/mcp_servers/*_mcp.py`, `scripts/assert_chunks.py`, `data/PROVENANCE.md`,
`.knowledge/api-contract.md`, `.knowledge/schema-db.md` (freeze).

## [MOCK-P1] markers
- All four "external systems" (Monitoring, ITSM, Tracker, CMDB) are simulators — mark clearly in code comments and later in the README/UI. Never referred to as real ServiceNow/Jira/Prometheus.

## Hard acceptance criteria (re-verify, don't just write)
- [ ] All synthetic datasets generated at the volumes specified in PRD §6.1, with `data/PROVENANCE.md` recording generator + date for each
- [ ] 4 simulators running as separate processes/endpoints, each with real field names for their ~12 demo fields
- [ ] 4 MCP servers running, each exposing the tool set frozen in `api-contract.md`
- [ ] `MaintenanceSignal` and DB schema frozen and pasted into `api-contract.md`/`schema-db.md`, both flipped to `active`
- [ ] SQLite fully populated per `schema-db.md`; Chroma collections populated and queryable
- [ ] `scripts/assert_chunks.py` passes clean against the full runbook corpus, including the deliberate trap runbook
- [ ] Agent-free gate script drives one scenario through all 4 MCP servers end to end, successfully

## CONTEXT CHECKPOINT — update on completion
- [.knowledge/api-contract.md](api-contract.md), [.knowledge/schema-db.md](schema-db.md) — flip to `active`, this is the freeze
- [.knowledge/citations.md](citations.md) — fill in generator script + date for every dataset row
- [.knowledge/state-progress.md](state-progress.md) — CURRENT PHASE → Phase 2, DONE list, FILE INVENTORY
- [.knowledge/domain-guardrails.md](domain-guardrails.md) — note chunker assertion script location if not already linked
