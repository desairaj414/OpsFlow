# Architecture

* [Tier Architecture](tier-architecture.md) - the layered system diagram, routing principle, and orchestration shape.
* [Provider Registry](provider-registry.md) - `backend/providers.py`, the multi-provider LLM registry with per-role model maps.
* [Provider Propagation](provider-propagation.md) - how a visitor's chosen provider reaches every LLM call site via HTTP headers + a contextvar.
* [Model Routing](model-routing.md) - the deterministic-vs-LLM-vs-SLM routing principle and a step-by-step technique table.
* [Cockpit UI](cockpit-ui.md) - the Next.js frontend: tab structure, Agent Trace Viewer, three-badge system, accessibility.
* [Overview Metrics](overview-metrics.md) - exactly how every number on the Overview dashboard is computed, and from what.
