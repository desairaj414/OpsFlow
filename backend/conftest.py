"""Ensures backend/ is importable as the package root for pytest (`from guardrails.x import y`,
`from correlation.x import y`, etc.) regardless of where pytest is invoked from.

Hitting Gemini's free-tier rate limit mid-suite (real gateway calls, no mocking)? Every test/script
context (pytest, eval/harness.py, scripts/pregenerate_demo_outputs.py, smoke_test.py) reads the
active provider from provider_context.get_active_provider(), which falls back to
providers.DEFAULT_PROVIDER outside a live request — and that's a plain env var, already
OPENROUTER_API_KEY-backed in this repo's .env. No code change needed to switch:

    DEFAULT_PROVIDER=openrouter python -m pytest

Works for both the LangChain-wrapped calls (api_client.get_llm(), used by diagnosis.py/planner.py)
and the raw-httpx ones (intake/vision_path.py's _extract() — this one has NO automatic in-process
fallback the way get_llm() does, so a 429 there always needs this env-var switch, not a retry).

Not a guaranteed fix, though — live-verified 2026-08-17 that the switch itself works (no more
Gemini 429s), but OpenRouter's own free tier is separately flaky (providers.py's registry comment
on "openrouter": a shared, variable-capacity upstream pool that fails unpredictably — 429s, spurious
401s, and dropped connections all observed). Worth trying when Gemini is the one rate-limiting; if
OpenRouter also fails, that's real flakiness on its end, not a config problem to chase further."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
