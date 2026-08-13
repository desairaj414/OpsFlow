---
type: Module
title: Structural Chunking
description: Splits runbooks/postmortems only on structural boundaries (numbered steps, headings), never on a character/token count — because a retrieved chunk of a runbook is an instruction toward a production action, and a chunk that drops a preceding "only if X" condition is dangerous, not just lossy.
resource: backend/chunking.py
tags: [guardrails, rag, chunking]
status: stable
generated: { by: "claude-sonnet-5/okf-produce", at: "2026-08-11T00:00:00Z" }
sources:
  - id: chunking-py
    resource: backend/chunking.py
    title: backend/chunking.py
    last_modified: 2026-08-07
  - id: domain-guardrails
    resource: .knowledge/domain-guardrails.md
    title: Domain — Guardrails & Bias Mitigation
    last_modified: 2026-08-07
---

# Overview

`chunk_runbook(path)` splits only on `### Step N` headings — a numbered step is atomic, staying
whole even across a simulated page-break marker in the source document. `chunk_postmortem(path)`
splits on `## Heading` boundaries.[^chunking-py] Neither ever splits on a character/token budget.

# Preamble inheritance

The rule that prevents the dangerous case in the description above: every prerequisites/warnings
block preceding a runbook's `## Steps` section is prepended to **every** step chunk from that
runbook (`Prerequisites: ... \n\n Step N: ...`), so a retrieved step never loses an "only if X"
condition just because it was retrieved in isolation from the rest of the document.[^chunking-py]

# Metadata

Every chunk carries a `heading_path` (e.g. `RB-014 › Steps › Step 3`) so a citation resolves to a
specific step, and a `class` tag (`remediation`/`patching`/`tuning`) that
[Planner Agent](/agents/planner-agent.md)'s `where={"class": runbook_class}` Chroma filter uses to
scope retrieval to the right runbook family. `chunk_postmortem` also passes through any other
frontmatter keys unchanged (e.g. `doc_type` on a Knowledge Base article), so a caller can tag
freeform content without this function needing to know every possible tag in advance.

# Verification

`scripts/assert_chunks.py` fails the build if a chunk begins mid-step, a numbered list is split
across chunks, a chunk lacks a heading path, or a code block is broken — run against the full
runbook/postmortem set including one deliberate trap runbook whose step 4 spans a simulated page
break, to prove the page-break marker is genuinely not treated as a split point.[^domain-guardrails]

[^chunking-py]: backend/chunking.py
[^domain-guardrails]: Domain — Guardrails & Bias Mitigation
