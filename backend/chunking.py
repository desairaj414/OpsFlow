"""Structural chunker per domain-guardrails.md "Chunking — implementation spec, not intention"
(PRD §6.4). Splits ONLY on structural boundaries (numbered steps for runbooks, headings for
postmortems) — never on a character/token count. A numbered step is atomic and is never split,
even across a simulated page break. Prerequisites/warnings attach to every step chunk in the
runbook (preamble inheritance) so a retrieved step never loses an "only if X" condition.
"""
import os
import re
from dataclasses import dataclass, field

_PAGE_BREAK_RE = re.compile(r"\n*<!-- PAGE BREAK.*?-->\n*", re.DOTALL)
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass
class Chunk:
    chunk_id: str
    content: str
    heading_path: str
    metadata: dict = field(default_factory=dict)


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm, text[m.end():]


def _clean_step_text(raw: str) -> str:
    """Removes the simulated page-break marker, joining both halves back into one seamless step —
    the marker exists to prove the chunker does NOT split there, not to mark a real boundary."""
    joined = _PAGE_BREAK_RE.sub(" ", raw)
    return re.sub(r"\s+", " ", joined).strip()


def chunk_runbook(path: str) -> list[Chunk]:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    frontmatter, body = _parse_frontmatter(text)
    rb_id = frontmatter.get("runbook_id", os.path.splitext(os.path.basename(path))[0])

    prereq_match = re.search(r"## Prerequisites\n(.*?)\n## Steps", body, re.DOTALL)
    preamble = prereq_match.group(1).strip() if prereq_match else ""

    # Split on "### Step N" boundaries only — a numbered step is atomic, page break or not.
    step_matches = list(re.finditer(r"### Step (\d+)\n(.*?)(?=\n### Step \d+|\Z)", body, re.DOTALL))
    chunks = []
    for m in step_matches:
        step_no = m.group(1)
        step_text = _clean_step_text(m.group(2))
        # Preamble inheritance: prerequisites/warnings attach to every step chunk (domain-guardrails.md).
        full_content = f"Prerequisites: {preamble}\n\nStep {step_no}: {step_text}" if preamble else f"Step {step_no}: {step_text}"
        chunks.append(Chunk(
            chunk_id=f"{rb_id}-step{step_no}",
            content=full_content,
            heading_path=f"{rb_id} › Steps › Step {step_no}",
            metadata={"runbook_id": rb_id, "class": frontmatter.get("class", ""), "step_no": int(step_no),
                      "is_trap_case": frontmatter.get("is_trap_case", "false")},
        ))
    return chunks


def chunk_postmortem(path: str) -> list[Chunk]:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    frontmatter, body = _parse_frontmatter(text)
    pm_id = frontmatter.get("postmortem_id", os.path.splitext(os.path.basename(path))[0])

    section_matches = list(re.finditer(r"## (.+?)\n(.*?)(?=\n## |\Z)", body, re.DOTALL))
    chunks = []
    for m in section_matches:
        heading = m.group(1).strip()
        content = re.sub(r"\s+", " ", m.group(2)).strip()
        if not content:
            continue
        chunks.append(Chunk(
            chunk_id=f"{pm_id}-{heading.lower().replace(' ', '_')}",
            content=f"{heading}: {content}",
            heading_path=f"{pm_id} › {heading}",
            # Passes through any other frontmatter key (e.g. doc_type/topic on a Knowledge Base
            # article) so callers can tag freeform content without this function knowing about every
            # possible tag — postmortem_id always wins over a same-named frontmatter key.
            metadata={**frontmatter, "postmortem_id": pm_id},
        ))
    return chunks
