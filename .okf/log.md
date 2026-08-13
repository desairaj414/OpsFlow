# Update Log

## 2026-08-11
* **Creation**: Initial OKF v0.2 bundle, distilled from `.knowledge/*.md` (24 files), `PRD_FINAL.md`,
  and the current backend/frontend source (`backend/providers.py`, `provider_context.py`,
  `api_client.py`, `main.py`, `orchestrator/`, `agents/`, `guardrails/`, `intake/`, `a2a/`,
  `mcp_servers/`, `db/schema.sql`, `frontend/src/lib/`, `frontend/src/components/`). Captures the
  system **as it stands mid-refactor**: a multi-provider LLM architecture (Gemini default,
  OpenRouter fallback, TCS retained as a legacy/gated provider) replacing the original
  single-hardcoded-TCS-endpoint design, plus the three public-hosting demo modes being built on top
  of it (Instant Demo, Bring Your Own Key, Free Demo Key). [Getting Started](getting-started.md);
  [Architecture](architecture/) (tier diagram, provider registry, provider propagation, model
  routing, cockpit UI, Overview-tab metrics); [Agents](agents/) (Supervisor + 6 specialists + the
  one A2A handoff); [Tools](tools/) (MCP layer); [Guardrails](guardrails/) (policy gate, blast
  radius, scrubber, bias mitigation, chunking); [Intake](intake/) (voice, vision);
  [Workflows](workflows/) (incident/patch/performance parity); [Data](data/) (SQLite + Chroma
  schema); [Demo Modes](demo-modes/) (the 3 public-hosting modes + the pregenerate script);
  [Decisions](decisions/) (two-level Supervisor topology, one A2A handoff, the multi-provider
  pivot, the fixed embeddings provider, no-checkpointing re-run behavior, real authentication).
  Deliberately excluded: the hour-by-hour hackathon schedule, the day-by-day execution/verification
  log (`state-progress.md`, `state-progress-history.md`), and the phase-gate checklists
  (`prd-phase-*.md`) — these are hackathon-process artifacts, not portable system knowledge.
