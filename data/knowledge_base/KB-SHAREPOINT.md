---
postmortem_id: KB-SHAREPOINT
doc_type: kb_article
topic: SharePoint
---

# SharePoint reference

## Overview

SharePoint Online hosts site collections and document libraries per tenant. Each site collection
has a storage quota drawn from the tenant's pooled storage; each document library inherits
permissions from its parent site unless permission inheritance is explicitly broken.

## Storage quotas

Document libraries fill up gradually as users sync large files or version history accumulates.
Versioning is the most common silent cause — a library with "keep every version" enabled can grow
several times larger than its visible content suggests. Quota-critical alerts should be triaged by
checking version history size before assuming new content is the cause.

## Permission errors

"Access denied" on a site collection is usually a broken permission-inheritance chain (a
subsite or library stopped inheriting from its parent and never got its own explicit grant), not a
missing license. Re-granting access at the wrong level (site vs. library vs. item) fixes the
symptom but not the root cause, and the same error tends to recur on the next new item.

## Sync client issues

The OneDrive/SharePoint sync client can crash-loop when a synced folder path exceeds Windows'
path-length limit, or when a file is locked by another process during sync. Restarting the sync
client clears a crash-loop but does not fix a path-length issue — that requires shortening the
library's folder structure.
