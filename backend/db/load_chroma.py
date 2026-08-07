"""Populates the 3 Chroma collections used at this point in the build (runbooks, postmortems,
ticket_history — negative_kb is embedded separately once the negative-KB retrieval path exists,
Phase 3). Chunks come from backend/chunking.py (structural, per domain-guardrails.md); embeddings
come from the real gateway (text-embedding-3-large), batched to keep call count sane (~700
individual chunks would otherwise be ~700 sequential HTTP round trips).

    python db/load_chroma.py         # (re)builds the Chroma collections
    python db/load_chroma.py --test  # also runs a retrieval self-check per collection
"""
# MUST be first — before any tiktoken/langchain import.
import os
os.environ["TIKTOKEN_CACHE_DIR"] = "./token"

import ssl
import urllib3

ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import csv
import json
import sys

import chromadb
import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__) + "/..")
import chunking  # noqa: E402

load_dotenv()

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
RUNBOOKS_DIR = os.path.join(DATA_DIR, "runbooks")
POSTMORTEMS_DIR = os.path.join(DATA_DIR, "postmortems")

BASE_URL = os.getenv("BASE_URL", "https://genailab.tcs.in/v1").rstrip("/")
API_KEY = os.getenv("API_KEY", "")
EMBED_MODEL = os.getenv("DEFAULT_EMBED_MODEL", "azure/genailab-maas-text-embedding-3-large")
BATCH_SIZE = 50


def embed_batch(client: httpx.Client, texts: list[str]) -> list[list[float]]:
    resp = client.post(
        f"{BASE_URL}/embeddings",
        json={"model": EMBED_MODEL, "input": texts},
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=60,
    )
    resp.raise_for_status()
    return [row["embedding"] for row in resp.json()["data"]]


def embed_all(client: httpx.Client, texts: list[str]) -> list[list[float]]:
    vectors = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        vectors.extend(embed_batch(client, batch))
    return vectors


def build_runbook_chunks() -> list[chunking.Chunk]:
    chunks = []
    for fname in sorted(os.listdir(RUNBOOKS_DIR)):
        if fname.endswith(".md"):
            chunks.extend(chunking.chunk_runbook(os.path.join(RUNBOOKS_DIR, fname)))
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

    with httpx.Client(verify=False) as http_client:
        rb_chunks = build_runbook_chunks()
        rb_coll = chroma_client.get_or_create_collection("runbooks")
        rb_coll.upsert(
            ids=[c.chunk_id for c in rb_chunks],
            embeddings=embed_all(http_client, [c.content for c in rb_chunks]),
            documents=[c.content for c in rb_chunks],
            metadatas=[{**c.metadata, "heading_path": c.heading_path} for c in rb_chunks],
        )
        print(f"runbooks collection: {len(rb_chunks)} chunks embedded")

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

        pm_coll = chroma_client.get_collection("postmortems")
        assert pm_coll.count() > 0
        print(f"PASS: postmortems collection has {pm_coll.count()} chunks")

        ticket_coll = chroma_client.get_collection("ticket_history")
        assert ticket_coll.count() == 500
        print(f"PASS: ticket_history collection has {ticket_coll.count()} tickets")

        print("\nSELF-TEST PASSED: all 3 Chroma collections populated and queryable.")
