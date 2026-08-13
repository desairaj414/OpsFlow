"""provider_context.py
───────────────────────
Per-request active-provider propagation. A visitor's chosen mode (Instant Demo / Bring Your Own
Key / Free Demo Key) is picked once, at login, on the frontend — but the LLM calls it needs to
affect happen many layers down (Supervisor -> specialist agents -> api_client.get_llm(), plus the
raw-httpx Whisper/vision calls in intake/voice_path.py and intake/vision_path.py). Threading an
explicit parameter through that whole call chain would mean changing every agent's frozen,
tested signature for a concern that isn't domain logic.

Instead: the frontend sends `X-LLM-Provider` (+ `X-LLM-Api-Key` for BYOK) as plain HTTP headers on
every request (see frontend/src/lib/api.js); a FastAPI dependency here reads them once per request
and sets a contextvar for that request's duration. Anything downstream (api_client.py,
voice_path.py, vision_path.py) reads the same contextvar. No header sent -> falls back to
providers.DEFAULT_PROVIDER, so local dev, smoke_test.py, and pytest (none of which send these
headers) behave exactly as before this refactor.

The BYOK key only ever lives in this contextvar for the lifetime of one request — it is never
written to audit_log, never logged, and never persisted anywhere.
"""
from contextvars import ContextVar
from dataclasses import dataclass

from fastapi import Header

import providers

_active_provider: ContextVar[str] = ContextVar("active_provider", default=providers.DEFAULT_PROVIDER)
_active_api_key: ContextVar[str | None] = ContextVar("active_api_key", default=None)

INSTANT_DEMO = "instant_demo"


@dataclass
class ProviderContext:
    provider: str  # one of providers.PROVIDERS keys, or INSTANT_DEMO
    is_instant_demo: bool


def get_provider_context(
    x_llm_provider: str | None = Header(default=None),
    x_llm_api_key: str | None = Header(default=None),
) -> ProviderContext:
    """FastAPI dependency — add to any endpoint that (directly or transitively) makes an LLM call,
    so the contextvars below are populated before that endpoint's handler runs."""
    if x_llm_provider == INSTANT_DEMO:
        _active_provider.set(providers.DEFAULT_PROVIDER)  # unused when is_instant_demo short-circuits, harmless default
        _active_api_key.set(None)
        return ProviderContext(provider=INSTANT_DEMO, is_instant_demo=True)

    resolved = providers.resolve_provider(x_llm_provider)
    _active_provider.set(resolved)
    _active_api_key.set(x_llm_api_key)
    return ProviderContext(provider=resolved, is_instant_demo=False)


def get_active_provider() -> str:
    """Read by api_client.py / voice_path.py / vision_path.py. Returns providers.DEFAULT_PROVIDER
    if no request has set the contextvar yet (e.g. a script run outside a FastAPI request, like
    smoke_test.py or pregenerate_demo_outputs.py)."""
    return _active_provider.get()


def get_active_api_key() -> str | None:
    """The visitor's own BYOK key for this request, if any (None for Free Demo Key / server-default
    sessions, in which case callers should use providers.api_key_for())."""
    return _active_api_key.get()


def set_provider_for_script(provider_name: str) -> None:
    """For standalone scripts run outside a FastAPI request (e.g.
    scripts/pregenerate_demo_outputs.py) that want to be explicit about which provider they're
    using rather than relying on providers.DEFAULT_PROVIDER's env-configured fallback."""
    if provider_name not in providers.PROVIDERS:
        raise ValueError(f"unknown provider {provider_name!r}")
    _active_provider.set(provider_name)
    _active_api_key.set(None)
