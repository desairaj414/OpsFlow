---
postmortem_id: KB-TEAMS
doc_type: kb_article
topic: Teams
---

# Microsoft Teams reference

## Overview

Teams routes chat, calls, and meeting notifications through a per-tenant notification queue. A
backed-up queue delays message delivery and meeting reminders without necessarily dropping a call
already in progress — the two symptoms have different causes and different urgency.

## Notification queue backlog

A queue backlog that keeps growing (not just a momentary spike) usually means a downstream consumer
(mobile push, email digest, or a connected line-of-business app via a Teams connector) is slow or
failing, not that Teams itself is overloaded. Clearing the backlog without fixing the slow consumer
just lets it refill.

## Meeting audio/video degradation

Audio/video quality issues are almost always network path problems (loss, jitter, or a
misconfigured QoS policy) between the client and the nearest Teams media relay, not a Teams service
outage — a single-user complaint is a network diagnosis question, a tenant-wide spike is a service
health question.

## Common failure signatures

"Sync client crash-looped" and "health check failing" against a Teams-related CI usually point at
the notification queue's worker process restarting under load rather than a hard outage — worth
checking queue depth before escalating as a full service disruption.
