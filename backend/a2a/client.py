"""Supervisor-side A2A client for the Diagnosis handoff. In-process (ASGI transport) by default
for dev/test, same pattern as orchestrator/mcp_wiring.py; production would point at the real
running endpoint (a2a/endpoint.py, port 9010) instead.
"""
import httpx

from orchestrator.contracts import SpecialistResult

_client: httpx.AsyncClient | None = None


def wire_in_process() -> None:
    global _client
    import a2a.endpoint as endpoint_module

    _client = httpx.AsyncClient(transport=httpx.ASGITransport(app=endpoint_module.app), base_url="http://a2a-diagnosis")


def _get_client() -> httpx.AsyncClient:
    if _client is None:
        wire_in_process()
    return _client


async def fetch_agent_card() -> dict:
    resp = await _get_client().get("/.well-known/agent-card.json")
    resp.raise_for_status()
    return resp.json()


async def invoke_diagnosis_via_a2a(incident_id: str, evidence: list[dict]) -> SpecialistResult:
    resp = await _get_client().post("/invoke", json={"incident_id": incident_id, "evidence": evidence})
    resp.raise_for_status()
    return SpecialistResult.model_validate(resp.json())
