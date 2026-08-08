---
postmortem_id: KB-AZURE-AD
doc_type: kb_article
topic: Azure AD
---

# Azure AD reference

## Overview

Azure AD Connect syncs on-premises identities to the cloud directory on a scheduled interval. A
sync interruption means the cloud directory is stale relative to on-prem, not that authentication
itself is down — existing sessions and already-synced accounts are unaffected.

## Sync interruption

The most common cause of a sync interruption is a credential expiring on the Azure AD Connect
service account, or a transient connectivity drop between the on-prem sync server and Azure AD. A
one-off interruption that self-clears on the next scheduled cycle is not worth escalating; a sync
that stays interrupted across multiple cycles means the connector itself needs attention.

## Conditional Access blocking sign-in

A Conditional Access policy blocking sign-in is doing exactly what it was configured to do — the
fix is rarely "disable the policy." Check which condition triggered the block (device compliance,
location, risk level) before assuming it's a misconfiguration; a policy that blocks a legitimate
user is more often the user's device or network falling outside an intentionally-set boundary.

## Certificate expiry

An expired certificate on a federation or sync connector fails closed by design — expect a hard
stop, not a degraded state, and plan certificate renewal ahead of the expiry date rather than
reacting to the outage it causes.
