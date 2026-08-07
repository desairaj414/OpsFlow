"""Generic, decoupled client factory for the enterprise OpenAI-compatible endpoint.

Import `config` first so TIKTOKEN_CACHE_DIR is set before langchain/tiktoken load.
"""
import config  # noqa: F401  (sets TIKTOKEN_CACHE_DIR as a side effect)

import httpx
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Corporate network MITM/self-signed certs -> SSL verification must be disabled.
_http_client = httpx.Client(verify=False)


def get_llm(model: str | None = None, temperature: float = 0.2) -> ChatOpenAI:
    """Return a ChatOpenAI instance bound to the enterprise endpoint."""
    return ChatOpenAI(
        base_url=config.BASE_URL,
        api_key=config.API_KEY,
        model=model or config.DEFAULT_CHAT_MODEL,
        temperature=temperature,
        http_client=_http_client,
    )


def get_embeddings(model: str | None = None) -> OpenAIEmbeddings:
    """Return an OpenAIEmbeddings instance bound to the enterprise endpoint."""
    return OpenAIEmbeddings(
        base_url=config.BASE_URL,
        api_key=config.API_KEY,
        model=model or config.DEFAULT_EMBED_MODEL,
        http_client=_http_client,
    )
