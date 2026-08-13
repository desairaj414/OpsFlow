# Agents

* [Supervisor](supervisor.md) - dispatch loop, schema re-validation, turn caps, workflow YAML.
* [Enrichment Agent](enrichment-agent.md) - deterministic evidence gathering across MCP tools + one real RAG lookup.
* [Diagnosis Agent](diagnosis-agent.md) - reasoning-role LLM root-cause hypothesis generation, citation enforcement.
* [Planner Agent](planner-agent.md) - RAG-grounded plan drafting, runbook-bounded action space, blast radius + policy gate.
* [Verification Agent](verification-agent.md) - the Fake Fix Detector, two-independent-signals rule.
* [Sync Agent](sync-agent.md) - writes the outcome back to ITSM + proposes a CMDB update.
* [Knowledge Agent](knowledge-agent.md) - seeds the Negative KB on a suppressed-symptom outcome.
* [A2A Handoff](a2a-handoff.md) - the one real Supervisor -> Diagnosis Agent-to-Agent handoff.
