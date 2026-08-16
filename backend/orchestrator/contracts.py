"""Typed contracts, pasted directly from api-contract.md's frozen shapes — the Supervisor
validates every specialist result against SpecialistResult before dispatching the next agent
(domain-agents.md: "validates each typed result against schema before continuing").
"""
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SpecialistResult(BaseModel):
    """The Supervisor <-> specialist handoff contract (api-contract.md)."""
    model_config = {"protected_namespaces": ()}  # `model_used` is a legitimate field name, not pydantic internals

    agent_name: str
    incident_id: str
    result: dict[str, Any]
    cited_artifact_ids: list[str] = Field(default_factory=list)
    confidence: float
    turns_used: int
    termination_reason: str  # must be explicit, never implicit
    # Agent Trace Viewer fields (Phase 4 atomic step 3, api-contract.md updated accordingly).
    # Optional with defaults so every existing construction call stays valid unchanged.
    latency_ms: float | None = None  # set by the Supervisor, which brackets each handoff
    tokens_used: int | None = None  # only set by LLM-calling agents (diagnosis, planner); None = no LLM call, not "unknown"
    transport: str = "in_process"  # "in_process" | "a2a" — Supervisor overrides to "a2a" for the one A2A handoff
    # The model id that actually answered (api_client.extract_model_used) — provider-dependent, not
    # a fixed string; None = no LLM call, or the response didn't report one. Added post-submission
    # when supervisor.py's audit-log write was found hardcoding TCS-only model names regardless of
    # the session's active provider (decisions-log.md's multi-provider pivot entry).
    model_used: str | None = None
    # Whether this agent's LLM call was served from orchestrator/cache.py's model_call_cache table
    # instead of a live gateway call (Phase 5 step 5, api-contract.md updated accordingly). None =
    # no LLM call (enrichment/verification/sync/knowledge never set this); True/False = a real
    # cache lookup happened. Lets the eval harness confirm "a replayed scenario doesn't re-hit the
    # gateway" from the trace alone, without re-deriving it from timing.
    cache_hit: bool | None = None

    @field_validator("confidence")
    @classmethod
    def _confidence_in_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"confidence must be in [0,1], got {v}")
        return v


class MaintenanceSignal(BaseModel):
    """The one canonical intake object, produced identically by all 3 intake paths
    (api-contract.md). Scrubber runs after modality conversion, before this object exists."""
    signal_id: str
    modality: str  # alert | voice | image
    received_at: str
    raw_ref: str | None = None  # not persisted beyond the run, see domain-privacy.md
    extracted_text: str
    candidate_ci_refs: list[str] = Field(default_factory=list)
    candidate_alert_refs: list[str] = Field(default_factory=list)
    confidence: float
    requires_human_confirmation: bool
    parsed_intent: str | None = None  # voice only
    # Whether guardrails/scrubber.py's local-Ollama free-text-name pass actually ran, set by the
    # voice/image intake paths (scrub() is not called for alert-modality signals, so this stays
    # None there): None = not applicable to this modality; True = it ran; False = it was attempted
    # and failed (e.g. no local Ollama reachable) — regex-based redaction (emails, phones, IPs,
    # etc.) still applied, but free-text person names in this signal may NOT be scrubbed.
    slm_pass_ran: bool | None = None

    @field_validator("modality")
    @classmethod
    def _modality_valid(cls, v: str) -> str:
        if v not in ("alert", "voice", "image"):
            raise ValueError(f"modality must be alert|voice|image, got {v!r}")
        return v
