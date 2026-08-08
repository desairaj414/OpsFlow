---
postmortem_id: KB-POWER-APPS
doc_type: kb_article
topic: Power Apps
---

# Power Apps & Power Platform environments reference

## Overview

A Power Platform environment bundles a Dataverse instance with the Power Apps/Power Automate
resources that run against it. Most environment-level incidents actually originate one layer down,
in Dataverse's own API limits or storage capacity, and surface as a generic environment alert.

## Dataverse API throttling

Dataverse enforces per-user and per-environment API request limits. A 429 (throttled) response
means the caller exceeded its allotted request rate in the current window — it is not an outage,
and it resolves on its own once the window rolls over. Repeated 429s from the same app usually mean
that app is making more granular API calls than necessary (e.g. one call per record in a loop
instead of a batched call).

## Environment capacity

Dataverse storage capacity is shared across an environment's tables, files, and logs. A capacity
warning should be triaged by checking which table is growing fastest (often audit log or attachment
storage) before requesting a blanket capacity increase.

## Connection refused errors

A "connection refused" against a Power Platform environment CI is most often a temporary
maintenance window or a expired/rotated connection credential on a custom connector, not a network
outage — check the connector's last successful call timestamp first.
