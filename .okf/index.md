---
okf_version: "0.2"
---

# OpsFlow Knowledge Bundle

OpsFlow (hackathon working name "Verascope") is a cross-stack maintenance control plane: a
Supervisor + specialist multi-agent system that takes IT operations signals (fault alerts, voice
commands, screenshots) through correlation, diagnosis, planning, guardrailed approval, execution,
verification, and knowledge capture — auditable at every step. Built for TCS AI Fridays Season 2
(Cross-Stack Maintenance Control Plane problem statement). FastAPI async backend, Next.js cockpit
frontend, MCP tool servers, one real A2A agent handoff, and a multi-provider LLM architecture that
lets the app run as a public, self-serve demo as well as against the original TCS GenAI Lab gateway.

# Start here

* [Getting Started](getting-started.md) - what this system does, the request lifecycle, and where to read next.

# Architecture

* [Architecture](architecture/) - tier diagram, LLM provider registry + propagation, model routing, the cockpit UI, and Overview-tab metrics.

# Agents

* [Agents](agents/) - the Supervisor and its 6 specialists (Enrichment, Diagnosis, Planner, Verification, Sync, Knowledge), plus the one A2A handoff.

# Tools

* [Tools](tools/) - the MCP tool-server layer over the simulated Monitoring/ITSM/Tracker/CMDB/Patch systems.

# Guardrails

* [Guardrails](guardrails/) - policy gate, blast radius, the PII/secrets scrubber, bias mitigations, and structural chunking.

# Multimodal intake

* [Intake](intake/) - voice (Whisper, closed-vocabulary intent) and vision (screenshot extraction) intake paths.

# Workflows

* [Workflows](workflows/) - the incident/patch/performance-tuning parity and why one declarative chain serves all three.

# Data

* [Data](data/) - the SQLite + Chroma schema shape.

# Demo modes

* [Demo Modes](demo-modes/) - Instant Demo, Bring Your Own Key, and Free Demo Key — how OpsFlow runs as a public deploy.

# Decisions

* [Decisions](decisions/) - notable, non-obvious engineering choices and their rationale.
