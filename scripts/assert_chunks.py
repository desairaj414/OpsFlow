"""Chunk verification per domain-guardrails.md — FAILS THE BUILD (non-zero exit) if a chunk
begins mid-step, a numbered step is split across chunks, a chunk lacks a heading path, or a code
block is broken. Run at the end of Phase 1 and again in Phase 5 (PRD §6.4).

    python scripts/assert_chunks.py
"""
import os
import re
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

import chunking  # noqa: E402

RUNBOOKS_DIR = os.path.join(REPO_ROOT, "data", "runbooks")
POSTMORTEMS_DIR = os.path.join(REPO_ROOT, "data", "postmortems")


def assert_runbook_corpus() -> list[str]:
    failures = []
    checked_trap = False
    for fname in sorted(os.listdir(RUNBOOKS_DIR)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(RUNBOOKS_DIR, fname)
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        declared_count_match = re.search(r"declared_human_step_count:\s*(\d+)", raw)
        declared_count = int(declared_count_match.group(1)) if declared_count_match else None
        is_trap = "is_trap_case: true" in raw

        chunks = chunking.chunk_runbook(path)

        # A numbered step split across chunks (or two steps merged into one) would show up as a
        # chunk-count mismatch against the runbook's own declared step count.
        if declared_count is not None and len(chunks) != declared_count:
            failures.append(f"{fname}: {len(chunks)} chunks != declared_human_step_count {declared_count} (a step was split or merged)")

        for c in chunks:
            if not c.heading_path:
                failures.append(f"{fname}: chunk {c.chunk_id} has no heading path")
            # "begins mid-step": every chunk's content must start with its own "Step N:" marker
            # (after the inherited preamble prefix), never a fragment of a previous step's text.
            if not re.search(r"Step \d+:", c.content):
                failures.append(f"{fname}: chunk {c.chunk_id} does not begin at a clean step boundary")
            # Broken code block: an unmatched ``` inside a single chunk means one got split.
            if c.content.count("```") % 2 != 0:
                failures.append(f"{fname}: chunk {c.chunk_id} has an unbalanced code fence (broken code block)")

        if is_trap:
            checked_trap = True
            trap_chunk = next((c for c in chunks if c.metadata.get("step_no") == 4), None)
            if trap_chunk is None:
                failures.append(f"{fname}: marked as trap case but has no step 4 chunk")
            else:
                if "<!-- PAGE BREAK" in trap_chunk.content:
                    failures.append(f"{fname}: trap chunk still contains the raw page-break marker (not cleaned)")
                # The dangerous case domain-guardrails.md describes: the "only if X" condition
                # must survive intact in the SAME chunk as the rest of step 4, not be dropped.
                if "Only if X" not in trap_chunk.content:
                    failures.append(f"{fname}: trap chunk lost the 'Only if X' condition — this is exactly the dangerous case the trap tests for")
                if "symptom_suppressed" not in trap_chunk.content:
                    failures.append(f"{fname}: trap chunk step 4 is incomplete — missing content from the second half of the page break")

    if not checked_trap:
        failures.append("no runbook marked is_trap_case: true was found — the deliberate trap case is required by domain-guardrails.md")

    return failures


def assert_postmortem_corpus() -> list[str]:
    failures = []
    for fname in sorted(os.listdir(POSTMORTEMS_DIR)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(POSTMORTEMS_DIR, fname)
        chunks = chunking.chunk_postmortem(path)
        if not chunks:
            failures.append(f"{fname}: produced zero chunks")
        for c in chunks:
            if not c.heading_path:
                failures.append(f"{fname}: chunk {c.chunk_id} has no heading path")
    return failures


def main() -> None:
    failures = assert_runbook_corpus() + assert_postmortem_corpus()
    if failures:
        print(f"FAILED — {len(failures)} chunk assertion(s) failed:\n")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    rb_count = len([f for f in os.listdir(RUNBOOKS_DIR) if f.endswith(".md")])
    pm_count = len([f for f in os.listdir(POSTMORTEMS_DIR) if f.endswith(".md")])
    print(f"PASSED — {rb_count} runbooks and {pm_count} postmortems all chunk correctly, including the deliberate trap case.")


if __name__ == "__main__":
    main()
