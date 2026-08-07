"""Shared Chroma retrieval — embeds a query via the real gateway (same model the collections
were embedded with) and queries the persistent Chroma store built in Phase 1
(backend/db/load_chroma.py). Used by Enrichment (ticket_history/postmortems precedent) and
Planner (runbook retrieval, scoped to the workflow's runbook class).
"""
import os

import chromadb
import httpx

import config  # noqa: F401  sets TIKTOKEN_CACHE_DIR + SSL bypass as a side effect

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHROMA_DIR = os.path.join(REPO_ROOT, "data", "chroma_db")

_chroma_client = None
_http_client = httpx.Client(verify=False)


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _chroma_client


def _embed(text: str) -> list[float]:
    resp = _http_client.post(
        f"{config.BASE_URL}/embeddings",
        json={"model": config.DEFAULT_EMBED_MODEL, "input": text},
        headers={"Authorization": f"Bearer {config.API_KEY}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def query_collection(collection_name: str, query_text: str, n_results: int = 3, where: dict | None = None) -> list[dict]:
    """Returns [{id, document, metadata, distance}, ...] ordered by similarity."""
    client = _get_chroma_client()
    collection = client.get_collection(collection_name)
    vector = _embed(query_text)
    kwargs = {"query_embeddings": [vector], "n_results": n_results}
    if where:
        kwargs["where"] = where
    result = collection.query(**kwargs)
    hits = []
    for i in range(len(result["ids"][0])):
        hits.append({
            "id": result["ids"][0][i],
            "document": result["documents"][0][i],
            "metadata": result["metadatas"][0][i],
            "distance": result["distances"][0][i] if result.get("distances") else None,
        })
    return hits
