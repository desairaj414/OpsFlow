---
postmortem_id: KB-POWER-AUTOMATE
doc_type: kb_article
topic: Power Automate
---

# Power Automate reference

## Overview

Power Automate flows run through a per-environment gateway that enforces API call limits per
connector. A flow that calls a throttled connector (SharePoint, Dataverse, or a custom connector)
too frequently gets its individual runs throttled, which is reported as a "flow run failed —
throttled" alert rather than a flow design error.

## Throttling

Throttling is a rate limit, not a hard failure — the same flow usually succeeds on retry once the
window resets. A flow that throttles repeatedly over hours, not just once, typically has a trigger
configured too aggressively (e.g. polling every minute against a connector meant for hourly use)
rather than a one-off traffic spike.

## Gateway degradation

"Throttling rate higher than baseline for 3 days" is a degradation signal, not a fault — it means
the gateway is trending toward its limit, not that anything has failed yet. These are handled as
performance-tuning work (raising a connector's allocated capacity or redesigning the trigger),
not as an incident.

## Diagnosing a failed run

A failed flow run's error usually names the specific connector step that failed. Confirm whether
the same connector appears in the CI's known throttling history before assuming a new root cause.
