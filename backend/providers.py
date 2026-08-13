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
