"""Generic, decoupled client factory for the enterprise OpenAI-compatible endpoint.

Import `config` first so TIKTOKEN_CACHE_DIR is set before langchain/tiktoken load.
"""
import config  # noqa: F401  (sets TIKTOKEN_CACHE_DIR as a side effect)

import httpx
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Corporate network MITM/self-signed certs -> SSL verification must be disabled.
_http_client = httpx.Client(verify=False)


def get_llm(model: str | None = None, temperature: float = 0.2, enable_offline_fallback: bool = True):
    """Return a chat model bound to the enterprise endpoint — transparently falls back to a local
    Ollama SLM (models-routing.md: "Offline fallback for demo resilience... must still run if the
    gateway dies mid-demo", PRD §3.2) if the enterprise call itself fails. `max_retries=1` bounds the
    SDK's default several-retries-with-backoff; `timeout=45` deliberately stays generous — DeepSeek
    R1 legitimately takes "tens of seconds" on a healthy gateway (models-routing.md), so a short
    timeout would falsely trigger the fallback on normal slow-but-working calls, not just real
    outages. Agents call this unchanged (`.invoke()`/`.content` both still work identically on the
    returned object, whichever backend actually answered)."""
    primary = ChatOpenAI(
        base_url=config.BASE_URL,
        api_key=config.API_KEY,
        model=model or config.DEFAULT_CHAT_MODEL,
        temperature=temperature,
        http_client=_http_client,
        timeout=45,
        max_retries=1,
    )
    if not enable_offline_fallback:
        return primary
    fallback = ChatOpenAI(
        base_url=config.OLLAMA_BASE_URL,
        api_key="ollama",  # unused by Ollama, the client just requires a non-empty string
        model=config.OLLAMA_FALLBACK_CHAT_MODEL,
        temperature=temperature,
        timeout=45,
        max_retries=0,
    )
    return primary.with_fallbacks([fallback])


def extract_token_usage(response) -> int | None:
    """Total token count from a ChatOpenAI response, if the gateway returned usage metadata.
    Used by the Agent Trace Viewer (Phase 4) — None means genuinely not reported, not zero."""
    usage = getattr(response, "usage_metadata", None)
    if usage and usage.get("total_tokens") is not None:
        return usage["total_tokens"]
    return None


class _EmbeddingsWithFallback:
    """`OpenAIEmbeddings` isn't a LangChain Runnable (no `.with_fallbacks()`, unlike `ChatOpenAI`) —
    this hand-rolls the same primary-then-local-Ollama fallback (models-routing.md) over the two
    methods the `Embeddings` interface actually needs, so it's still a drop-in for anything expecting
    one (`embed_documents`/`embed_query`)."""

    def __init__(self, primary: OpenAIEmbeddings, fallback: OpenAIEmbeddings):
        self._primary = primary
        self._fallback = fallback

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            return self._primary.embed_documents(texts)
        except Exception:
            return self._fallback.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        try:
            return self._primary.embed_query(text)
        except Exception:
            return self._fallback.embed_query(text)


def get_embeddings(model: str | None = None, enable_offline_fallback: bool = True):
    """Return an embeddings model bound to the enterprise endpoint — same offline-fallback behavior
    as `get_llm()` (models-routing.md), via local Ollama's `gte-large`. CAUTION if wiring this into a
    Chroma-backed retrieval path: the fallback's `gte-large` produces 1024-dim vectors vs. the
    enterprise model's 3072-dim — querying an already-indexed collection with a different-dimension
    fallback vector raises Chroma's `InvalidDimensionException`, not a graceful degradation (this is
    exactly why `orchestrator/retrieval.py`'s `_embed()` does NOT use this fallback — see its
    docstring). Only safe end-to-end if the same model embedded that collection in the first place."""
    primary = OpenAIEmbeddings(
        base_url=config.BASE_URL,
        api_key=config.API_KEY,
        model=model or config.DEFAULT_EMBED_MODEL,
        http_client=_http_client,
        timeout=20,
        max_retries=1,
    )
    if not enable_offline_fallback:
        return primary
    fallback = OpenAIEmbeddings(
        base_url=config.OLLAMA_BASE_URL,
        api_key="ollama",
        model=config.OLLAMA_FALLBACK_EMBED_MODEL,
        timeout=30,
        max_retries=0,
        check_embedding_ctx_length=False,  # Ollama's embeddings endpoint doesn't support tiktoken pre-chunking
    )
    return _EmbeddingsWithFallback(primary, fallback)
