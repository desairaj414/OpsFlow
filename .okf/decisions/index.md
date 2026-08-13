# Decisions

* [Two-Level Supervisor](two-level-supervisor.md) - why Supervisor + specialists, not a deeper hierarchy, a free agent mesh, or an off-the-shelf framework.
* [One A2A Handoff](one-a2a-handoff.md) - why exactly one protocol handoff travels over A2A, not all agent traffic.
* [Multi-Provider Architecture](multi-provider-architecture.md) - replacing the single hardcoded TCS endpoint with a provider registry, to support public hosting.
* [Embeddings Fixed Provider](embeddings-fixed-provider.md) - why embeddings never follow a visitor's chosen LLM provider.
* [No Workflow Checkpointing](no-workflow-checkpointing.md) - why approving a paused plan re-runs the workflow fresh instead of resuming it.
* [Real Authentication](real-authentication.md) - superseding the original "no real auth" call with genuine per-account credentials.
