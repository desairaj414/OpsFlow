---
type: System
title: A2A Handoff — Supervisor to Diagnosis
description: The one real Agent-to-Agent protocol handoff in OpsFlow — a genuinely HMAC-signed, discoverable Agent Card, invoked over HTTP (in-process ASGI transport in this build) instead of a plain function call.
tags: [a2a, protocol, agents]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: agent-card-py
    resource: backend/a2a/agent_card.py
    title: backend/a2a/agent_card.py
    last_modified: 2026-08-07
  - id: client-py
    resource: backend/a2a/client.py
    title: backend/a2a/client.py
    last_modified: 2026-08-07
---

# Overview

Every other Supervisor <-> specialist call in the chain is in-process, using the typed
`SpecialistResult` Python contract directly. The Supervisor -> Diagnosis handoff is the one
deliberate exception, chosen as the most demo-prominent reasoning step — see
[One A2A Handoff](/decisions/one-a2a-handoff.md) for why exactly one, not all of them.[^client-py]

# Agent Card

```json
{
  "name": "diagnosis-agent",
  "description": "Root-cause hypothesis generation & ranking...",
  "capabilities": ["generate_diagnosis"],
  "endpoint": "http://localhost:9010/invoke",
  "signature": "<hex HMAC-SHA256 over the other 4 fields, canonical JSON, sorted keys>"
}
```

The signature is a real, verifiable HMAC-SHA256 over the canonical (sorted-key) JSON of the other 4
fields, keyed by a local-only secret (`A2A_SECRET`) — `verify_agent_card()` rejects any tampered
field. This is explicitly documented as a hackathon-scope simplification: a production deployment
would use asymmetric/PKI signing, not a shared local secret.[^agent-card-py]

# Discovery and invocation

- **Discovery**: `GET /.well-known/agent-card.json`.
- **Invocation**: `POST /invoke` with `{incident_id, evidence}`, returning a `SpecialistResult`.

`backend/a2a/endpoint.py` runs the real Diagnosis agent behind this HTTP surface (standalone on
port 9010, or via in-process ASGI transport for tests/dev — `backend/a2a/client.py`'s
`wire_in_process()` mounts `a2a/endpoint.py`'s FastAPI app directly onto an `httpx.AsyncClient`, no
real socket needed). The Supervisor calls `invoke_diagnosis_via_a2a()` instead of calling
[Diagnosis](diagnosis-agent.md) as a plain Python function — this is the one place `transport` on
`SpecialistResult` is set to `"a2a"` rather than the default `"in_process"`.[^client-py]

# Runs locally, calls nothing outbound

Both the MCP layer and this A2A endpoint run locally and call nothing outbound — the pre-empt line
for the "gateway vs. external system" distinction: OpsFlow's own protocol implementations are local
infrastructure, not a dependency on a third-party service.

[^agent-card-py]: backend/a2a/agent_card.py
[^client-py]: backend/a2a/client.py
