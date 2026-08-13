---
type: System
title: MCP Tool Layer
description: One local MCP server per simulated external system (Monitoring, ITSM, Tracker, CMDB, Patch Source), exposing typed tools an agent calls instead of hand-rolled API glue.
tags: [mcp, protocol, integration]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: api-contract
    resource: .knowledge/api-contract.md
    title: API & Agent Contracts
    last_modified: 2026-08-07
  - id: cmdb-mcp-py
    resource: backend/mcp_servers/cmdb_mcp.py
    title: backend/mcp_servers/cmdb_mcp.py
    last_modified: 2026-08-07
---

# Overview

Each of Monitoring / ITSM / Tracker / CMDB / Patch Source exposes typed tools over MCP (Model
Context Protocol) rather than bespoke HTTP calls scattered through agent code. Every server
(`backend/mcp_servers/{monitoring,itsm,tracker,cmdb,patch}_mcp.py`, built on `mcp.server.fastmcp.FastMCP`)
wraps a corresponding FastAPI simulator (`backend/mcp_servers/simulators/*.py`, ports 9001-9005) and
can run either as a real stdio-transport MCP server or, for tests/dev, self-test in-process over an
ASGI transport with no real port required.[^cmdb-mcp-py] Everything the app itself needs at runtime
is wired in-process via `orchestrator/mcp_wiring.py` — the standalone ports only matter if a
simulator is run standalone.

# Tool set per server

| Server | Tools |
|---|---|
| Monitoring | `list_alerts`, `get_metric_series(ci_id)` |
| ITSM | `create_ticket`, `update_ticket`, `add_work_note`, `get_ticket(sys_id)` |
| Tracker | `create_issue`, `link_issue`, `transition_issue`, `get_issue` |
| CMDB | `get_ci(id)`, `get_relationships(ci_id)`, `propose_ci_update` (records a proposal only — never mutates the CI directly) |
| Patch Source | `get_pending_patches(ci_id)`, `get_change_calendar(scope)` — `scope` is `global`, an environment name, or a specific `ci_id`; the server always includes `global` windows alongside the requested scope |

[^api-contract]

# `propose_ci_update` never writes

Confirmed by the CMDB MCP server's own self-test: after calling `propose_ci_update`, a follow-up
`get_ci` shows the field unchanged — the human-approval gate for actually applying a CI update is
documented as not yet built, not silently skipped.[^cmdb-mcp-py]

# Why simulated systems, not real ones

Monitoring/ITSM/Tracker/CMDB are OpsFlow's own FastAPI mocks — explicitly labelled as such in the
UI, never presented as third-party SaaS. A real ServiceNow Personal Developer Instance was
considered and rejected: it hibernates after roughly 24 hours, releases after 10 days, carries a
possible waitlist and licence-framing risk, and a real instance can't produce on-demand scenarios
(a 50-alert storm, 6-month CMDB drift, a planted credential) the way a simulator can. See
[Decisions](/decisions/) for the full rejection record.

# Consumers

[Enrichment Agent](/agents/enrichment-agent.md) (CMDB, Monitoring, Patch Source), [Sync Agent](/agents/sync-agent.md)
(ITSM, CMDB), [Supervisor](/agents/supervisor.md) (ITSM, to create the incident's ticket),
[Planner Agent](/agents/planner-agent.md) (Patch Source, for maintenance-window scheduling).

[^api-contract]: API & Agent Contracts
