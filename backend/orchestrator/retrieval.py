"""Shared Chroma retrieval — embeds a query via the real gateway (same model the collections
were embedded with) and queries the persistent Chroma store built in Phase 1
(backend/db/load_chroma.py). Used by Enrichment (ticket_history/postmortems precedent) and
Planner (runbook retrieval, scoped to the workflow's runbook class).
"""
import os
import time

import chromadb
import httpx

import config  # noqa: F401  sets TIKTOKEN_CACHE_DIR + TCS_NETWORK-gated SSL bypass as a side effect
import providers

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHROMA_DIR = os.path.join(REPO_ROOT, "data", "chroma_db")

_chroma_client = None
_EMBED_PROVIDER_CFG = providers.PROVIDERS[providers.EMBEDDING_PROVIDER]
_http_client = httpx.Client(verify=not _EMBED_PROVIDER_CFG["needs_ssl_bypass"])


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _chroma_client


def _embed(text: str) -> list[float]:
    # Deliberately NO offline fallback here (unlike api_client.get_llm/get_embeddings): every
    # existing Chroma collection (runbooks/postmortems/ticket_history) is already indexed with
    # providers.EMBEDDING_PROVIDER's vectors, at that model's dimension. A query-time-only fallback
    # to a different-dimension model (Ollama's gte-large, or any other provider a visitor's session
    # happens to be using) would raise Chroma's InvalidDimensionException on every query, not
    # degrade gracefully — confirmed by testing directly. This is also why embeddings deliberately
    # do NOT read provider_context's per-session active provider the way api_client.get_llm() does
    # — embeddings are a fixed, server-controlled operation on a shared index, not a per-visitor
    # choice. A real offline embedding fallback here would need a fully separate, Ollama-indexed
    # collection, not a same-collection swap; out of scope for now.
    #
    # Retry-on-429 IS added (same provider, same model — not a fallback, just resilience): Gemini's
    # free-tier embeddings quota is tighter than TCS's was and gets hit under back-to-back retrieval
    # calls (confirmed: the backend test suite's several Planner/Enrichment tests running in quick
    # succession reliably 429s without this). This does not touch the dimension-mismatch concern
    # above at all.
    for attempt in range(3):
        resp = _http_client.post(
            f"{_EMBED_PROVIDER_CFG['base_url'].rstrip('/')}/embeddings",
            json={"model": _EMBED_PROVIDER_CFG["embedding_model"], "input": text},
            headers={"Authorization": f"Bearer {providers.api_key_for(providers.EMBEDDING_PROVIDER, None)}"},
            timeout=30,
        )
        # Confirmed 2026-08-11 via a live 429: this is Gemini's free-tier embed_content per-minute
        # quota (1000/min), not a daily cap like the chat-model finding above — the response's own
        # "Please retry in Ns" is consistently close to 60s, so wait a full minute, not a short
        # backoff, or the retry just re-hits the same still-active window.
        if resp.status_code == 429 and attempt < 2:
            time.sleep(65)
            continue
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
