"""Populates the 3 Chroma collections used at this point in the build (runbooks, postmortems,
ticket_history — negative_kb is embedded separately once the negative-KB retrieval path exists,
Phase 3). Chunks come from backend/chunking.py (structural, per domain-guardrails.md); embeddings
come from providers.EMBEDDING_PROVIDER — a fixed, server-controlled provider regardless of which
provider any given visitor's session uses (see providers.py: re-embedding this same data with a
different-dimension model would make an already-built collection unqueryable), batched to keep
call count sane (~700 individual chunks would otherwise be ~700 sequential HTTP round trips).

    python db/load_chroma.py         # (re)builds the Chroma collections
    python db/load_chroma.py --test  # also runs a retrieval self-check per collection
"""
# MUST be first — before any tiktoken/langchain import.
import os
import sys

sys.path.insert(0, os.path.dirname(__file__) + "/..")
import config  # noqa: E402  sets TIKTOKEN_CACHE_DIR + TCS_NETWORK-gated SSL bypass as a side effect
import providers  # noqa: E402

import csv
import json
import time

import chromadb
import httpx

import chunking  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
RUNBOOKS_DIR = os.path.join(DATA_DIR, "runbooks")
POSTMORTEMS_DIR = os.path.join(DATA_DIR, "postmortems")
KNOWLEDGE_BASE_DIR = os.path.join(DATA_DIR, "knowledge_base")

_EMBED_PROVIDER_CFG = providers.PROVIDERS[providers.EMBEDDING_PROVIDER]
BASE_URL = _EMBED_PROVIDER_CFG["base_url"].rstrip("/")
API_KEY = providers.api_key_for(providers.EMBEDDING_PROVIDER, None)
EMBED_MODEL = _EMBED_PROVIDER_CFG["embedding_model"]
BATCH_SIZE = 50


def embed_batch(client: httpx.Client, texts: list[str], retries: int = 5) -> list[list[float]]:
    # Gemini's free-tier embeddings quota is far more restrictive than TCS's was (real 429s hit
    # even at BATCH_SIZE=50) — retry with backoff rather than failing the whole rebuild partway
    # through, matching scripts/pregenerate_demo_outputs.py's approach to the same free-tier limit.
    for attempt in range(retries):
        resp = client.post(
            f"{BASE_URL}/embeddings",
            json={"model": EMBED_MODEL, "input": texts},
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=60,
        )
        if resp.status_code == 429 and attempt < retries - 1:
            wait = 15 * (attempt + 1)
            print(f"  rate limited, waiting {wait}s (attempt {attempt + 1}/{retries})...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return [row["embedding"] for row in resp.json()["data"]]
    raise RuntimeError("Gave up on embed_batch after repeated 429s")


def embed_all(client: httpx.Client, texts: list[str]) -> list[list[float]]:
    vectors = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        vectors.extend(embed_batch(client, batch))
        time.sleep(2)  # space batches out — free-tier RPM, not just burst limits
    return vectors


def build_runbook_chunks() -> list[chunking.Chunk]:
    chunks = []
    for fname in sorted(os.listdir(RUNBOOKS_DIR)):
        if fname.endswith(".md"):
            chunks.extend(chunking.chunk_runbook(os.path.join(RUNBOOKS_DIR, fname)))
    for c in chunks:
        c.metadata["doc_type"] = "runbook"
    return chunks


def build_knowledge_base_chunks() -> list[chunking.Chunk]:
    """Reference articles (Teams/SharePoint/Power Automate/Power Apps/Azure AD) — chunked with
    chunk_postmortem (heading-based, the right fit for freeform reference text vs. chunk_runbook's
    numbered-step structure) and upserted into the SAME "runbooks" Chroma collection as the actual
    runbooks, tagged doc_type=kb_article. Deliberately no `class` metadata (remediation/patching/
    tuning) — agents/planner.py's retrieval filters on `where={"class": runbook_class}`, so these
    reference-only chunks are naturally invisible to plan-drafting and can never be cited as an
    executable runbook step."""
    if not os.path.isdir(KNOWLEDGE_BASE_DIR):
        return []
    chunks = []
    for fname in sorted(os.listdir(KNOWLEDGE_BASE_DIR)):
        if fname.endswith(".md"):
            chunks.extend(chunking.chunk_postmortem(os.path.join(KNOWLEDGE_BASE_DIR, fname)))
    return chunks


def build_postmortem_chunks() -> list[chunking.Chunk]:
    chunks = []
    for fname in sorted(os.listdir(POSTMORTEMS_DIR)):
        if fname.endswith(".md"):
            chunks.extend(chunking.chunk_postmortem(os.path.join(POSTMORTEMS_DIR, fname)))
    return chunks


def build_ticket_records() -> list[dict]:
    with open(os.path.join(DATA_DIR, "tickets.csv"), encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    records = []
    for row in rows:
        text = f"[{row['type']}/{row['status']}/{row['priority']}] {row['short_description']} (CI: {row['ci_id']})"
        records.append({"id": row["sys_id"], "content": text, "metadata": {"type": row["type"], "status": row["status"], "ci_id": row["ci_id"]}})
    return records


def main() -> None:
    os.makedirs(CHROMA_DIR, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

    with httpx.Client(verify=not _EMBED_PROVIDER_CFG["needs_ssl_bypass"]) as http_client:
        rb_chunks = build_runbook_chunks()
        kb_chunks = build_knowledge_base_chunks()
        all_chunks = rb_chunks + kb_chunks
        # hnsw:search_ef default (10) is too small once a filtered query's candidate pool (e.g.
        # where={"class": "remediation"} across every matching runbook) exceeds it — hnswlib then
        # raises "Cannot return the results in a contigious 2D array. Probably ef or M is too small"
        # instead of just returning fewer results. 500 covers this collection's full size with room
        # to grow. Only takes effect on first creation — a `.modify()` is needed if the collection
        # already exists (see errors-solved.md).
        rb_coll = chroma_client.get_or_create_collection("runbooks", metadata={"hnsw:search_ef": 500})
        rb_coll.upsert(
            ids=[c.chunk_id for c in all_chunks],
            embeddings=embed_all(http_client, [c.content for c in all_chunks]),
            documents=[c.content for c in all_chunks],
            metadatas=[{**c.metadata, "heading_path": c.heading_path} for c in all_chunks],
        )
        print(f"runbooks collection: {len(rb_chunks)} runbook chunks + {len(kb_chunks)} knowledge base chunks embedded")

        pm_chunks = build_postmortem_chunks()
        pm_coll = chroma_client.get_or_create_collection("postmortems")
        pm_coll.upsert(
            ids=[c.chunk_id for c in pm_chunks],
            embeddings=embed_all(http_client, [c.content for c in pm_chunks]),
            documents=[c.content for c in pm_chunks],
            metadatas=[{**c.metadata, "heading_path": c.heading_path} for c in pm_chunks],
        )
        print(f"postmortems collection: {len(pm_chunks)} chunks embedded")

        tickets = build_ticket_records()
        ticket_coll = chroma_client.get_or_create_collection("ticket_history")
        ticket_coll.upsert(
            ids=[t["id"] for t in tickets],
            embeddings=embed_all(http_client, [t["content"] for t in tickets]),
            documents=[t["content"] for t in tickets],
            metadatas=[t["metadata"] for t in tickets],
        )
        print(f"ticket_history collection: {len(tickets)} tickets embedded")


if __name__ == "__main__":
    main()

    if "--test" in sys.argv:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

        rb_coll = chroma_client.get_collection("runbooks")
        assert rb_coll.count() > 0
        got = rb_coll.get(where={"is_trap_case": "true"})
        assert len(got["ids"]) >= 1, "trap runbook chunks not retrievable by metadata filter"
        print(f"PASS: runbooks collection has {rb_coll.count()} chunks, trap case retrievable by metadata filter")

        kb_got = rb_coll.get(where={"doc_type": "kb_article"})
        assert len(kb_got["ids"]) >= 5, f"expected >=5 knowledge base chunks, got {len(kb_got['ids'])}"
        assert all("class" not in md for md in kb_got["metadatas"]), "a kb_article chunk has a `class` field — it would leak into Planner's runbook_class retrieval filter"
        print(f"PASS: {len(kb_got['ids'])} knowledge base chunks present, correctly invisible to Planner's class filter")

        pm_coll = chroma_client.get_collection("postmortems")
        assert pm_coll.count() > 0
        print(f"PASS: postmortems collection has {pm_coll.count()} chunks")

        ticket_coll = chroma_client.get_collection("ticket_history")
        assert ticket_coll.count() == 500
        print(f"PASS: ticket_history collection has {ticket_coll.count()} tickets")

        print("\nSELF-TEST PASSED: all 3 Chroma collections populated and queryable.")
