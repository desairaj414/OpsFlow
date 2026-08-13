"""Diagnosis agent — root-cause hypothesis generation & ranking, using the active provider's
"reasoning"-role model (models-routing.md: "the only step genuinely needing multi-step reasoning
over conflicting evidence" — see providers.py for the per-provider role map, e.g. DeepSeek R1 on
TCS). Citation enforcement: a hypothesis whose cited_artifact_ids is empty or cites an artifact not
in the evidence bundle is dropped before it is ever included in the returned result — functionally
"suppressed at generation" from the system's perspective, never filtered after the fact downstream.
"""
import json

import api_client
from orchestrator.contracts import SpecialistResult
from orchestrator.limits import TERMINATION_CAP_EXCEEDED, TurnCapExceeded, TurnTracker


def _build_prompt(evidence: list[dict]) -> str:
    valid_ids = [e["artifact_id"] for e in evidence]
    evidence_block = "\n".join(f"- [{e['artifact_id']}] ({e['source_type']}): {e['extract']}" for e in evidence)
    return f"""You are diagnosing an IT incident. Below is the evidence gathered so far, each tagged
with its artifact ID. Generate 2-4 ranked root-cause hypotheses. EVERY hypothesis MUST cite at
least one artifact ID from this exact list — do not invent artifact IDs, do not cite an ID not
listed below: {valid_ids}

EVIDENCE:
{evidence_block}

Respond with ONLY valid JSON (no markdown fences), this exact shape:
{{"hypotheses": [{{"text": "...", "confidence": 0.0, "cited_artifact_ids": ["..."]}}]}}
"""


def _parse_and_filter(raw_content: str, valid_ids: set[str]) -> list[dict]:
    content = raw_content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
    parsed = json.loads(content)
    hypotheses = parsed.get("hypotheses", [])

    surviving = []
    for h in hypotheses:
        cited = h.get("cited_artifact_ids") or []
        # Citation enforcement: empty citations, or any citation outside the evidence bundle -> dropped.
        if not cited or not set(cited).issubset(valid_ids):
            continue
        surviving.append({
            "text": h.get("text", ""),
            "confidence": max(0.0, min(1.0, float(h.get("confidence", 0.0)))),
            "cited_artifact_ids": cited,
        })
    return sorted(surviving, key=lambda h: h["confidence"], reverse=True)


async def run_diagnosis(incident_id: str, evidence: list[dict]) -> SpecialistResult:
    tracker = TurnTracker("diagnosis")
    valid_ids = {e["artifact_id"] for e in evidence}
    llm = api_client.get_llm(role="reasoning", temperature=0)
    prompt = _build_prompt(evidence)

    hypotheses: list[dict] = []
    termination_reason = "no_valid_hypotheses"
    response = None
    try:
        while True:
            tracker.use_turn()
            # .ainvoke(), not .invoke() — see planner.py's identical comment. This is the single
            # slowest call in the chain (DeepSeek R1, "tens of seconds"), so it's also the one whose
            # blocking hurts most.
            response = await llm.ainvoke(prompt)
            try:
                hypotheses = _parse_and_filter(response.content, valid_ids)
                termination_reason = "hypotheses_generated" if hypotheses else "no_valid_hypotheses"
                break
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                if tracker.remaining() == 0:
                    termination_reason = TERMINATION_CAP_EXCEEDED
                    break
                continue  # retry, consumes another turn
    except TurnCapExceeded:
        termination_reason = TERMINATION_CAP_EXCEEDED

    cited_artifact_ids = sorted({aid for h in hypotheses for aid in h["cited_artifact_ids"]})
    top_confidence = hypotheses[0]["confidence"] if hypotheses else 0.0

    return SpecialistResult(
        agent_name="diagnosis", incident_id=incident_id,
        result={"hypotheses": hypotheses}, cited_artifact_ids=cited_artifact_ids,
        confidence=top_confidence, turns_used=tracker.turns_used, termination_reason=termination_reason,
        tokens_used=api_client.extract_token_usage(response) if response is not None else None,
    )
