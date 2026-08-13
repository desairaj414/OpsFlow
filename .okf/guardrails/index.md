# Guardrails

* [Policy Gate](policy-gate.md) - the deterministic rule engine gating block/needs-approval/allow decisions.
* [Blast Radius](blast-radius.md) - BFS over the CMDB adjacency graph, feeds the policy gate's thresholds.
* [Scrubber](scrubber.md) - the PII/secrets redaction pipeline (regex + local SLM), reversible tokenisation.
* [Bias Mitigation](bias-mitigation.md) - the 9-row bias table and how each mitigation is actually implemented.
* [Chunking](chunking.md) - structural-boundary-only document chunking, so a retrieved runbook step never loses a governing precondition.
