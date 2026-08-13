"""providers.py
────────────────
Registry of LLM providers OpsFlow can talk to, plus the active-provider propagation mechanism
that lets a per-visitor choice (Instant Demo / Bring Your Own Key / Free Demo Key) reach every
LLM call site without threading a parameter through the whole Supervisor -> specialist chain.

Unlike EduCare's single `default_model` per provider, OpsFlow's agents call distinct models for
distinct roles (reasoning, structured-JSON drafting, general/default, vision) — see
models-routing.md. Each provider entry below carries a `roles` map instead of one model id.

Usage:
    from providers import PROVIDERS, DEMO_PROVIDER, resolve_provider
    from provider_context import get_active_provider, get_active_api_key

    provider = PROVIDERS[get_active_provider()]
    model = provider["roles"]["reasoning"]
"""
import os

import httpx

import config

# model roles used across the agent chain (models-routing.md):
#   default     - general/summarization/self-check (was gpt-4o-mini/gpt-4.1-nano)
#   reasoning   - root-cause hypothesis generation (was DeepSeek R1) — needs genuine multi-step
#                 reasoning over conflicting evidence, tolerate higher latency
#   structured  - remediation-plan drafting / chat filter-extraction, must return valid JSON
#                 reliably at a normal token budget (models-routing.md flagged that some
#                 reasoning-heavy free models burn the budget on hidden thinking tokens and
#                 truncate structured output — picked accordingly below)
#   vision      - screenshot/error-image extraction

PROVIDERS: dict[str, dict] = {
    "gemini": {
        "label": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        # All four roles point at gemini-flash-lite-latest, not a distinct model per role.
        # gemini-flash-latest (aliasing gemini-3.6-flash as of this build) was the original pick for
        # reasoning/vision, but live-testing 2026-08-11 found two separate, disqualifying problems:
        # (1) with a capped max_tokens budget it burns most/all of it on invisible thinking tokens,
        # returning finish_reason="length" with truncated/unparseable JSON (same failure EduCare's
        # providers.py documents for the same reason); (2) its free tier caps at a hard **20
        # requests/day** (confirmed via a real 429: "GenerateRequestsPerDayPerProjectPerModel-
        # FreeTier... quotaValue: 20, model: gemini-3.6-flash") — for "Free Demo Key" mode, meant to
        # always work for public visitors, that's not a usable budget; a handful of test runs
        # exhausted it. gemini-flash-lite-latest has none of these problems at the same prompts
        # (confirmed: full valid JSON, finish_reason="stop", no truncation) and a far higher
        # effective free-tier ceiling — the sacrifice is reasoning depth, not reliability, an
        # explicit tradeoff for a public free-tier demo where availability matters most.
        "roles": {
            "default": "gemini-flash-lite-latest",
            "reasoning": "gemini-flash-lite-latest",
            "structured": "gemini-flash-lite-latest",
            "vision": "gemini-flash-lite-latest",
        },
        "embedding_model": "gemini-embedding-001",  # live-verified 2026-08-11, 3072-dim
        "vision": True,
        "supports_transcription": False,
        "needs_ssl_bypass": False,
        "key_hint": "Get a free key at aistudio.google.com/apikey",
        "pricing_url": "https://ai.google.dev/gemini-api/docs/pricing",
        # model_source drives the BYOK model picker (LoginModeSelector.jsx):
        #   "static" - Gemini's own /models listing isn't reliable enough to trust for a picker, so
        #              offer this hand-curated, live-verified list instead (tier is a best-effort
        #              label, not a guarantee — free/paid eligibility shifts under a given model id).
        #   "fetch"  - call GET {base_url}/models with the visitor's key and use whatever comes back.
        #   "manual" - no listing to fetch; the visitor types a model id.
        "model_source": "static",
        "model_choices": [
            {"id": "gemini-flash-lite-latest", "label": "Flash-Lite Latest", "tier": "free"},
            {"id": "gemini-flash-latest", "label": "Flash Latest (reasoning model)", "tier": "free"},
            {"id": "gemini-pro-latest", "label": "Pro Latest (higher quality, slower)", "tier": "paid"},
        ],
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        # Live-verified 2026-08-11 against a real OPENROUTER_API_KEY, models-routing.md-style: each
        # tested with the actual prompt shape its role sends (structured-JSON remediation/diagnosis
        # prompts, a real error-dialog screenshot for vision), not just a trivial ping. The original
        # guesses (llama-3.3-70b, deepseek-r1, qwen2.5-vl) don't exist in OpenRouter's current free
        # catalog at all — replaced with ids confirmed live via GET /models (`:free` suffix).
        # KNOWN ISSUE: OpenRouter's free tier routes through a shared, variable-capacity upstream
        # pool ("Darkbloom"/"Nvidia" providers, per response metadata) — the exact same request can
        # return 200, a real 429 rate-limit, or a spurious 401 "Missing Authentication header" (not
        # an actual auth failure — confirmed by immediate retry succeeding with the identical key),
        # unpredictably. `api_client.get_llm()`'s existing `max_retries=1` + Ollama offline fallback
        # already cover this; no extra retry logic added here.
        "roles": {
            "default": "openai/gpt-oss-20b:free",
            "reasoning": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
            "structured": "openai/gpt-oss-20b:free",
            "vision": "nvidia/nemotron-nano-12b-v2-vl:free",
        },
        "embedding_model": None,  # OpenRouter has no embeddings endpoint; never used for embeddings
        "vision": True,
        "supports_transcription": False,
        "needs_ssl_bypass": False,
        "key_hint": "Get a free key at openrouter.ai/keys",
        "tier_hint": "Model ids ending in :free are free tier; everything else is paid, billed to your OpenRouter credits.",
        "pricing_url": "https://openrouter.ai/models",
        "model_source": "fetch",
    },
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "roles": {},  # no baked default — BYOK visitors always pick a model via fetch, see model_source
        "embedding_model": None,  # never EMBEDDING_PROVIDER; a visitor's own key never touches Chroma
        "whisper_model": "whisper-1",
        "vision": True,
        "supports_transcription": True,
        "needs_ssl_bypass": False,
        "key_hint": "Get a key at platform.openai.com/api-keys (paid, no free tier)",
        "pricing_url": "https://openai.com/api/pricing/",
        "model_source": "fetch",
    },
    "grok": {
        "label": "xAI Grok",
        "base_url": "https://api.x.ai/v1",
        "roles": {},
        "embedding_model": None,
        "vision": True,
        "supports_transcription": False,
        "needs_ssl_bypass": False,
        "key_hint": "Get a key at console.x.ai (paid, no free tier)",
        "pricing_url": "https://x.ai/api",
        "model_source": "fetch",
    },
    "custom": {
        "label": "Custom (OpenAI-compatible)",
        "base_url": "",  # visitor-supplied at login time (X-LLM-Base-Url), see resolve_base_url()
        "roles": {},
        "embedding_model": None,
        "vision": True,
        "supports_transcription": False,
        "needs_ssl_bypass": False,
        "key_hint": "Any OpenAI-compatible chat completions endpoint",
        "model_source": "fetch",
    },
    "tcs": {
        "label": "TCS GenAI Lab (legacy, internal network only)",
        "base_url": config.BASE_URL,
        "roles": {
            "default": "azure/genailab-maas-gpt-4.1-nano",
            "reasoning": "azure_ai/genailab-maas-DeepSeek-R1",
            "structured": "azure/genailab-maas-gpt-4.1-nano",
            "vision": "genailab-maas-gpt-4o",
        },
        "embedding_model": config.DEFAULT_EMBED_MODEL,
        "whisper_model": "azure/genailab-maas-whisper",
        "vision": True,
        "supports_transcription": True,
        "needs_ssl_bypass": True,
        "key_hint": "TCS-issued key; only reachable from the TCS network",
        "note": (
            "Legacy/gated — kept for parity with the original hackathon build. Not reachable from "
            "the public deploy; selecting it there will simply fail every call."
        ),
        # TCS's own /models listing isn't public/documented, unlike the other gateways — ask instead.
        "model_source": "manual",
    },
}

# Backs "Free Demo Key" mode and the fixed embeddings pin (see api_client.get_embeddings) — the
# key comes from GEMINI_API_KEY, set as a platform secret in the public deploy, never committed.
DEMO_PROVIDER = "gemini"

# Provider used to embed/query Chroma, regardless of which provider a visitor's own session is on
# (decisions-log.md already rejected a same-collection cross-provider embeddings fallback once —
# different embedding models produce different-dimension vectors, which raises Chroma's
# InvalidDimensionException on every query against an already-indexed collection). Embeddings are
# an internal system operation on a shared index, not something a visitor's BYOK key should touch.
EMBEDDING_PROVIDER = DEMO_PROVIDER

DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", DEMO_PROVIDER)


def resolve_provider(name: str | None) -> str:
    """Validate a provider name from a request header, falling back to DEFAULT_PROVIDER for
    anything missing/unrecognized (keeps local dev / smoke_test.py / any caller that never sends
    the header working exactly as before this refactor)."""
    if name and name in PROVIDERS:
        return name
    return DEFAULT_PROVIDER


def api_key_for(provider: str, byok_key: str | None) -> str:
    """Resolve the actual API key to use for a given provider + optional visitor-supplied BYOK key."""
    if byok_key:
        return byok_key
    if provider == "gemini":
        return config.GEMINI_API_KEY
    if provider == "openrouter":
        return config.OPENROUTER_API_KEY
    if provider == "tcs":
        return config.API_KEY
    return ""


def resolve_base_url(provider: str, override_base_url: str | None) -> str:
    """A BYOK visitor's explicit choice wins (only meaningful for `custom`, whose registry entry has
    no base_url of its own); every other provider ignores the override and keeps its fixed base_url,
    so a stray header can't redirect a curated provider's calls elsewhere."""
    base_url = PROVIDERS[provider]["base_url"] or override_base_url
    if not base_url:
        raise ValueError(f"No base URL configured for provider {provider!r} — Custom requires one.")
    return base_url


def resolve_model(provider: str, role: str, override_model: str | None) -> str:
    """A BYOK visitor's explicit model choice (X-LLM-Model header, set after the login-screen fetch/
    validate step) always wins over the curated per-role default — even for gemini/openrouter/tcs,
    whose `roles` map only backs Free Demo Key / Instant Demo sessions that never send this header."""
    if override_model:
        return override_model
    model = PROVIDERS[provider]["roles"].get(role)
    if not model:
        raise ValueError(
            f"No model configured for provider {provider!r} role {role!r} — Bring Your Own Key "
            "sessions must select a model at login."
        )
    return model


# ─── BYOK model-picker helpers (LoginModeSelector.jsx, via main.py's /providers/* endpoints) ──────
# Mirror EduCare's providers.py fetch_models()/validate_key() — same one-shot, no-persistence
# approach, adapted to read needs_ssl_bypass from this registry instead of a flat function param.
_verified_client = httpx.Client(verify=True)
_unverified_client = httpx.Client(verify=False)


def _byok_client_for(provider: str) -> httpx.Client:
    return _unverified_client if PROVIDERS[provider].get("needs_ssl_bypass") else _verified_client


def fetch_models(provider: str, api_key: str, base_url: str | None = None, timeout: float = 8.0) -> list[str] | None:
    """Best-effort GET {base_url}/models. Returns a sorted model-id list on success, or None if the
    endpoint doesn't exist / errors / times out — the frontend falls back to a manual model-id field
    in that case."""
    if provider not in PROVIDERS:
        return None
    try:
        url = resolve_base_url(provider, base_url).rstrip("/") + "/models"
    except ValueError:
        return None
    try:
        resp = _byok_client_for(provider).get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=timeout)
        resp.raise_for_status()
        ids = [m["id"] for m in resp.json().get("data", []) if "id" in m]
        return sorted(ids) if ids else None
    except Exception:
        return None


def probe_transcription_support(provider: str, api_key: str, base_url: str | None = None, timeout: float = 6.0) -> bool | None:
    """Whether {base_url}/audio/transcriptions actually exists, for the one provider where that's
    genuinely unknown ahead of time.

    For every curated provider (gemini/openrouter/openai/grok/tcs), `supports_transcription` is a
    verified, static fact about that provider's API surface — not something that varies by key or
    account credits (Gemini's OpenAI-compat layer has never exposed this endpoint, on any tier) — so
    this just returns the registry value for them without a network call; probing a known API
    surface live would only add latency and a new false-negative failure mode (a network blip during
    the probe) for zero accuracy gain.

    For `custom`, we have no idea what a visitor's arbitrary OpenAI-compatible endpoint supports, so
    this POSTs a throwaway multipart payload and classifies by status code alone: 404 means the route
    doesn't exist at all (no transcription); anything else (200, 400, 422, even 500) means some
    handler answered at that path, so the endpoint is there even though our garbage payload itself
    was rejected. Unlike vision (which rides the same /chat/completions path as regular text, so a
    rejected test image can't be distinguished from "unsupported"), transcription has its own
    dedicated URL, making 404-vs-not a clean, reliable signal.

    Returns None if the probe itself couldn't complete (network error/timeout) — callers should treat
    that as "couldn't verify," not as a confirmed "no"."""
    if provider != "custom":
        return PROVIDERS.get(provider, {}).get("supports_transcription")
    try:
        url = resolve_base_url(provider, base_url).rstrip("/") + "/audio/transcriptions"
    except ValueError:
        return None
    try:
        resp = _byok_client_for(provider).post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": ("probe.wav", b"\x00" * 44, "audio/wav")},
            data={"model": "probe"},
            timeout=timeout,
        )
        return resp.status_code != 404
    except Exception:
        return None


def validate_key(
    provider: str, api_key: str, model: str, base_url: str | None = None, timeout: float = 15.0
) -> tuple[bool, str | None]:
    """Minimal one-token completion call so a visitor's bad BYOK key/model is caught at login, not on
    the first real workflow run. Returns (ok, error_message)."""
    if provider not in PROVIDERS:
        return False, "Unknown provider"
    try:
        url = resolve_base_url(provider, base_url).rstrip("/") + "/chat/completions"
    except ValueError as e:
        return False, str(e)
    try:
        resp = _byok_client_for(provider).post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": "Reply with OK."}], "max_tokens": 5},
            timeout=timeout,
        )
        if resp.status_code == 200:
            return True, None
        return False, f"{resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, str(e)
