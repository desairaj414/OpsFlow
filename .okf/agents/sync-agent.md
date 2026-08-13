---
type: Module
title: Sync Agent
description: Writes the workflow outcome back to the simulated ITSM system as a work note + status update, and on a verified fix, proposes (never applies) a CMDB field update — one consistent record across systems. Deterministic, no LLM.
resource: backend/agents/sync.py
tags: [agents, itsm, cmdb]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: sync-py
    resource: backend/agents/sync.py
    title: backend/agents/sync.py
    last_modified: 2026-08-11
---

# Overview

`run_sync(incident_id, sys_id, ci_id, verification_status, plan)` always writes a work note
summarizing the verification status and plan (`itsm_mcp.add_work_note`) and moves the ticket to a
ServiceNow-style resolved (`"7"`) or in-progress (`"2"`) state code
(`itsm_mcp.update_ticket`).[^sync-py]

# CMDB proposal, not a write

Only when `verification_status == "verified_resolved"` does it call `cmdb_mcp.propose_ci_update`,
setting `last_verified_at`. Per [MCP Tool Layer](/tools/mcp-tool-layer.md), this is a **proposal**
recorded by the CMDB simulator, not a direct write — a human approval step to actually apply it is
documented as not yet built.

# Consumers

Feeds `local_tickets` (see [Database Schema](/data/database-schema.md)) via
`main.py`'s `_persist_ticket_snapshot`, which mirrors the ITSM ticket's resulting state into a
local, restart-durable record for the Tickets tab.

[^sync-py]: backend/agents/sync.py
