"""A2A Agent Card — Supervisor -> Diagnosis is the ONE handoff that travels over A2A (chosen
2026-08-07, recorded in domain-agents.md; everything else stays in-process with typed Python
contracts, per decisions-log.md "one A2A handoff only"). "Signed" here means a real HMAC-SHA256
signature over the canonical card JSON — verifiable, not decorative — using a local-only secret;
a production deployment would use asymmetric keys, out of scope for this hackathon build. This
endpoint runs locally and calls nothing outbound (PRD §0 pre-empt language).
"""
import hashlib
import hmac
import json
import os

A2A_SECRET = os.getenv("A2A_SECRET", "dev-only-change-me-a2a")


def _sign(unsigned_card: dict) -> str:
    canonical = json.dumps(unsigned_card, sort_keys=True).encode()
    return hmac.new(A2A_SECRET.encode(), canonical, hashlib.sha256).hexdigest()


def build_agent_card(name: str, description: str, capabilities: list[str], endpoint: str) -> dict:
    card = {"name": name, "description": description, "capabilities": capabilities, "endpoint": endpoint}
    return {**card, "signature": _sign(card)}


def verify_agent_card(card: dict) -> bool:
    signature = card.get("signature")
    unsigned = {k: v for k, v in card.items() if k != "signature"}
    return hmac.compare_digest(signature or "", _sign(unsigned))


DIAGNOSIS_AGENT_CARD = build_agent_card(
    name="diagnosis-agent",
    description="Root-cause hypothesis generation & ranking (DeepSeek R1). Every hypothesis cites "
                "at least one evidence artifact ID; uncited hypotheses are dropped before being returned.",
    capabilities=["generate_diagnosis"],
    endpoint="http://localhost:9010/invoke",
)
