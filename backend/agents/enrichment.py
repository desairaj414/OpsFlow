"""Enrichment agent — gathers evidence across MCP-exposed systems, attaches artifact IDs
(domain-agents.md). Deterministic: pulling CI facts, relationships, metrics, and precedent via
retrieval is not a reasoning task (arch-overview.md routing principle) — no LLM call in this agent.
"""
import mcp_servers.cmdb_mcp as cmdb_mcp
import mcp_servers.monitoring_mcp as monitoring_mcp
from orchestrator.contracts import SpecialistResult
from orchestrator.limits import TERMINATION_CAP_EXCEEDED, TurnCapExceeded, TurnTracker
from orchestrator.retrieval import query_collection

# Token discipline (arch-overview.md): evidence extracts truncated, agents see IDs + extracts,
# never whole documents.
_EXTRACT_MAX_CHARS = 240


def _trend_summary(series: list[dict]) -> str | None:
    if len(series) < 2:
        return None
    start_mem, end_mem = float(series[0]["memory_pct"]), float(series[-1]["memory_pct"])
    start_lat, end_lat = float(series[0]["latency_ms"]), float(series[-1]["latency_ms"])
    if end_mem - start_mem > 15 or end_lat - start_lat > 200:
        return f"degradation trend: memory {start_mem:.0f}%->{end_mem:.0f}%, latency {start_lat:.0f}ms->{end_lat:.0f}ms"
    return f"stable: memory {start_mem:.0f}%->{end_mem:.0f}%, latency {start_lat:.0f}ms->{end_lat:.0f}ms"


async def run_enrichment(incident_id: str, ci_id: str, alerts: list[dict]) -> SpecialistResult:
    tracker = TurnTracker("enrichment")
    evidence: list[dict] = []
    cited_artifact_ids: list[str] = []

    try:
        tracker.use_turn()
        ci = await cmdb_mcp.get_ci(ci_id=ci_id)
        evidence.append({
            "artifact_id": ci_id, "source_type": "cmdb",
            "extract": f"{ci['type']} in {ci['environment']}, criticality {ci['criticality']}, patch_level {ci['patch_level']}",
            "confidence": 1.0,
        })
        cited_artifact_ids.append(ci_id)

        relationships = await cmdb_mcp.get_relationships(ci_id=ci_id)
        rel_list = relationships["relationships"]
        if rel_list:
            evidence.append({
                "artifact_id": ci_id, "source_type": "cmdb_relationship",
                "extract": f"{len(rel_list)} related CIs: " + ", ".join(f"{r['relation_type']}->{r['related_ci_id']}" for r in rel_list[:5]),
                "confidence": 1.0,
            })

        for alert in alerts:
            cited_artifact_ids.append(alert["id"])
            evidence.append({
                "artifact_id": alert["id"], "source_type": "alert",
                "extract": f"[{alert['source']}/{alert['category']}/{alert['severity']}] {str(alert['raw_payload'])[:_EXTRACT_MAX_CHARS]}",
                "confidence": 1.0,
            })

        tracker.use_turn()
        try:
            metrics = await monitoring_mcp.get_metric_series(ci_id=ci_id)
            trend = _trend_summary(metrics["series"])
            if trend:
                artifact_id = f"METRICS-{ci_id}"
                evidence.append({"artifact_id": artifact_id, "source_type": "metrics", "extract": trend, "confidence": 0.8})
                cited_artifact_ids.append(artifact_id)
        except Exception:
            pass  # no metric series for this CI — not every CI has one, not an error

        tracker.use_turn()
        try:
            query_text = f"{ci['type']} {alerts[0]['category']} incident" if alerts else ci["type"]
            precedent = query_collection("ticket_history", query_text, n_results=2)
            for hit in precedent:
                evidence.append({
                    "artifact_id": hit["id"], "source_type": "ticket_history_precedent",
                    "extract": hit["document"][:_EXTRACT_MAX_CHARS], "confidence": max(0.0, 1.0 - (hit["distance"] or 0)),
                })
                cited_artifact_ids.append(hit["id"])
        except Exception:
            pass  # Chroma/gateway unavailable — enrichment degrades gracefully, doesn't crash the chain

        termination_reason = "evidence_gathering_complete"
    except TurnCapExceeded:
        termination_reason = TERMINATION_CAP_EXCEEDED

    return SpecialistResult(
        agent_name="enrichment", incident_id=incident_id,
        result={"evidence": evidence}, cited_artifact_ids=cited_artifact_ids,
        confidence=1.0 if evidence else 0.0,
        turns_used=tracker.turns_used, termination_reason=termination_reason,
    )
