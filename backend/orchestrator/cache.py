"""Model-call cache (Phase 5 step 5) — hash(prompt_version, scrubbed/deterministic prompt) ->
response, backed by the model_call_cache SQLite table that db/schema.sql already declared but no
code ever wrote to. Scoped to diagnosis.py and planner.py: both call their LLM at temperature=0
specifically for reproducibility (domain-guardrails.md pillar (d): "temperature 0 for decision
steps, Replay button") — caching an exact-match input is consistent with that goal, not a
deviation from it, and it's what lets a replayed scenario (Scenario Launcher, eval harness, the
Instant Demo pregenerate script) return the same verified answer without a live gateway call.

Deliberately NOT wired into main.py's two chat call sites (_classify_chat_intent/_chat_app_help)
— those are free-form user text that varies on every message, so an exact-match cache would almost
never hit; the reproducibility argument above doesn't apply to them the way it does to the
decision-critical agent chain.

check_cache/store_cache are exposed separately, not one auto-caching `ainvoke` wrapper: both
diagnosis.py and planner.py retry the same prompt on a parse failure (TurnTracker), and a retry's
whole point is a fresh sample when the first one was bad. The call sites therefore only
check_cache() on their first attempt (never on a retry — retrying against the cache would just
replay the same failure forever) and only store_cache() a response that actually parsed (so a
failed attempt never poisons the cache for a future replay)."""
import hashlib
import os
import sqlite3
from dataclasses import dataclass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(REPO_ROOT, "data", "app.db")


@dataclass
class CachedCall:
    content: str
    tokens: int | None
    model: str | None


def cache_key(prompt_version: str, cache_input: str) -> str:
    return hashlib.sha256(f"{prompt_version}|{cache_input}".encode("utf-8")).hexdigest()


def check_cache(key: str) -> CachedCall | None:
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT response, tokens, model FROM model_call_cache WHERE hash = ?", (key,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    response, tokens, model = row
    return CachedCall(content=response, tokens=tokens, model=model)


def store_cache(key: str, response: str, tokens: int | None, latency_ms: float, model: str | None) -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO model_call_cache (hash, response, tokens, latency_ms, model) VALUES (?,?,?,?,?)",
            (key, response, tokens, latency_ms, model),
        )
        conn.commit()
    finally:
        conn.close()
