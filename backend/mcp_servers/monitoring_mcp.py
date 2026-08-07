"""MCP server wrapping the Monitoring simulator — exposes the typed tool set from
api-contract.md ("Monitoring: list_alerts, get_metric_series(ci_id)") over MCP instead of
bespoke HTTP, per PRD §3.8. Calls the simulator (mcp_servers/simulators/monitoring.py) over
HTTP — this file is the tool/integration layer, the simulator is the fake external system below it.

    python mcp_servers/monitoring_mcp.py         # runs the MCP server (stdio transport)
    python mcp_servers/monitoring_mcp.py --test  # in-process self-test (ASGI transport, no real port)
"""
import os
import sys

import httpx
from mcp.server.fastmcp import FastMCP

SIMULATOR_BASE_URL = os.getenv("MONITORING_SIM_URL", "http://localhost:9001")

mcp = FastMCP("monitoring")
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=SIMULATOR_BASE_URL)
    return _client


@mcp.tool()
async def list_alerts(ci_id: str | None = None, category: str | None = None, severity: str | None = None) -> dict:
    """List alerts from the Monitoring simulator, optionally filtered by CI, category, or severity."""
    params = {k: v for k, v in {"ci_id": ci_id, "category": category, "severity": severity}.items() if v}
    resp = await _get_client().get("/api/v2/alerts", params=params)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def get_metric_series(ci_id: str) -> dict:
    """Get the metric time series (cpu/memory/latency/error_rate) for a given CI."""
    resp = await _get_client().get(f"/api/v1/ci/{ci_id}/metrics")
    resp.raise_for_status()
    return resp.json()


async def _self_test() -> None:
    # Ensure backend/ is on sys.path regardless of how this script was invoked, so the
    # mcp_servers.simulators.* import below resolves.
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    import mcp_servers.simulators.monitoring as sim_module

    global _client
    _client = httpx.AsyncClient(transport=httpx.ASGITransport(app=sim_module.app), base_url="http://sim")

    result = await list_alerts()
    alerts = result["data"]["alerts"]
    assert len(alerts) > 0, "no alerts returned via MCP tool"
    print(f"PASS list_alerts (via MCP tool): {len(alerts)} alerts")

    sample_ci = alerts[0]["ci_id"]
    result = await list_alerts(ci_id=sample_ci)
    filtered = result["data"]["alerts"]
    assert all(a["ci_id"] == sample_ci for a in filtered)
    print(f"PASS list_alerts filtered (via MCP tool): {len(filtered)} for {sample_ci}")

    import json
    import os as _os

    data_dir = _os.path.join(_os.path.dirname(__file__), "..", "..", "data")
    with open(_os.path.join(data_dir, "metrics_index.json"), encoding="utf-8") as f:
        index = json.load(f)
    metrics_ci = index["sampled_ci_ids"][0]
    result = await get_metric_series(ci_id=metrics_ci)
    assert len(result["series"]) > 0
    print(f"PASS get_metric_series (via MCP tool): {len(result['series'])} points for {metrics_ci}")

    await _client.aclose()
    print("\nSELF-TEST PASSED: Monitoring MCP tools work end to end against the simulator (in-process).")


if __name__ == "__main__":
    if "--test" in sys.argv:
        import asyncio

        asyncio.run(_self_test())
    else:
        mcp.run(transport="stdio")
