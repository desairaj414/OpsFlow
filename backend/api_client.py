"""Provider-aware client factory — builds a chat/embeddings client for whichever provider is
active on the current request (Instant Demo / Bring Your Own Key / Free Demo Key / legacy TCS),
per provider_context.py. See providers.py for the provider registry and per-role model maps.

Import `config` first so TIKTOKEN_CACHE_DIR is set before langchain/tiktoken load.
"""
import config  # noqa: F401  (sets TIKTOKEN_CACHE_DIR as a side effect)

import httpx
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

import providers
from provider_context import get_active_api_key, get_active_base_url, get_active_model, get_active_provider

# One client per trust level, mirroring EduCare's api_client.py split — `verify=False` only ever
# applies to the `tcs` provider's own calls (its base_url sits behind the TCS network's MITM
# proxy), every other provider gets normal certificate verification.
_verified_client = httpx.Client(verify=True)
_unverified_client = httpx.Client(verify=False)


def _http_client_for(provider_cfg: dict) -> httpx.Client:
    return _unverified_client if provider_cfg.get("needs_ssl_bypass") else _verified_client


def get_llm(role: str = "default", temperature: float = 0.2, enable_offline_fallback: bool = True):
    """Return a chat model bound to whichever provider is active on this request (contextvar set
    by provider_context.get_provider_context(), read via get_active_provider()/get_active_api_key()
    — falls back to providers.DEFAULT_PROVIDER for callers outside a request, e.g. smoke_test.py).
    `role` selects the model from that provider's models-routing.md-derived role map (`default`,
    `reasoning`, `structured`, `vision`) instead of a literal model id, so the same call site works
    unchanged across every provider.

    Falls back in order: (1) OpenRouter using the platform's own OPENROUTER_API_KEY, but ONLY for
    Free Demo Key sessions (no visitor-supplied key, active provider is providers.DEMO_PROVIDER) —
    never for Bring Your Own Key, where the visitor's own key/provider choice is exclusive by design
    (silently rerouting their request through the deployer's OpenRouter key would spend the
    deployer's quota without consent and break the "your key, your quota" promise); (2) a local
    Ollama SLM (models-routing.md: "Offline fallback for demo resilience... must still run if the
    gateway dies mid-demo", PRD §3.2). Both are skipped if their key/reachability requirement isn't
    met — Ollama in particular is a no-op on a hosted deploy with no local Ollama process (it just
    fails and falls through), which is exactly why the OpenRouter step was added: it's the only
    fallback in this chain that's actually reachable from a public deploy, giving Free Demo Key
    sessions real resilience if the shared Gemini key hits its quota, instead of a hard failure with
    a fallback that can never succeed off the TCS network / a local dev machine.

    `max_retries=1` bounds the SDK's default several-retries-with-backoff; `timeout=45` deliberately
    stays generous — reasoning-role calls legitimately take "tens of seconds" on a busy provider, so
    a short timeout would falsely trigger the fallback on normal slow-but-working calls, not just
    real outages. Agents call this unchanged (`.invoke()`/`.content` both still work identically on
    the returned object, whichever backend actually answered)."""
    provider_name = get_active_provider()
    provider_cfg = providers.PROVIDERS[provider_name]
    active_key = get_active_api_key()
    api_key = providers.api_key_for(provider_name, active_key)
    primary = ChatOpenAI(
        base_url=providers.resolve_base_url(provider_name, get_active_base_url()),
        api_key=api_key,
        model=providers.resolve_model(provider_name, role, get_active_model()),
        temperature=temperature,
        http_client=_http_client_for(provider_cfg),
        timeout=45,
        max_retries=1,
    )
    if not enable_offline_fallback:
        return primary

    fallbacks = []
    is_server_key_session = active_key is None  # None (not BYOK) vs "" (BYOK visitor left it blank, shouldn't reach here)
    if is_server_key_session and provider_name == providers.DEMO_PROVIDER and config.OPENROUTER_API_KEY:
        openrouter_cfg = providers.PROVIDERS["openrouter"]
        fallbacks.append(ChatOpenAI(
            base_url=openrouter_cfg["base_url"],
            api_key=config.OPENROUTER_API_KEY,
            model=providers.resolve_model("openrouter", role, None),
            temperature=temperature,
            http_client=_http_client_for(openrouter_cfg),
            timeout=45,
            max_retries=1,
        ))
    fallbacks.append(ChatOpenAI(
        base_url=config.OLLAMA_BASE_URL,
        api_key="ollama",  # unused by Ollama, the client just requires a non-empty string
        model=config.OLLAMA_FALLBACK_CHAT_MODEL,
        temperature=temperature,
        timeout=45,
        max_retries=0,
    ))
    return primary.with_fallbacks(fallbacks)


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
    """Return an embeddings model — always bound to providers.EMBEDDING_PROVIDER (a fixed,
    server-controlled provider/key), never the current request's active session provider. See
    providers.py and orchestrator/retrieval.py's `_embed()` docstring: every Chroma collection is
    already indexed at one specific embedding model's dimension, so embeddings can't follow a
    visitor's BYOK choice the way chat calls do without breaking every existing query.

    Same offline-fallback behavior as `get_llm()` (models-routing.md), via local Ollama's
    `gte-large`. CAUTION if wiring this into a Chroma-backed retrieval path: the fallback's
    `gte-large` produces 1024-dim vectors vs. the enterprise model's 3072-dim — querying an
    already-indexed collection with a different-dimension fallback vector raises Chroma's
    `InvalidDimensionException`, not a graceful degradation (this is exactly why
    `orchestrator/retrieval.py`'s `_embed()` does NOT use this fallback — see its docstring). Only
    safe end-to-end if the same model embedded that collection in the first place."""
    provider_cfg = providers.PROVIDERS[providers.EMBEDDING_PROVIDER]
    primary = OpenAIEmbeddings(
        base_url=provider_cfg["base_url"],
        api_key=providers.api_key_for(providers.EMBEDDING_PROVIDER, None),
        model=model or provider_cfg["embedding_model"],
        http_client=_http_client_for(provider_cfg),
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
