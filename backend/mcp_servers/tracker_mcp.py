"""MCP server wrapping the Tracker simulator — exposes the typed tool set from api-contract.md
("Tracker: create_issue, link_issue, transition_issue, get_issue") over MCP, per PRD §3.8.

    python mcp_servers/tracker_mcp.py         # runs the MCP server (stdio transport)
    python mcp_servers/tracker_mcp.py --test  # in-process self-test (ASGI transport, no real port)
"""
import os
import sys

import httpx
from mcp.server.fastmcp import FastMCP

SIMULATOR_BASE_URL = os.getenv("TRACKER_SIM_URL", "http://localhost:9003")

mcp = FastMCP("tracker")
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=SIMULATOR_BASE_URL)
    return _client


@mcp.tool()
async def get_issue(key: str) -> dict:
    """Get a single tracker issue by key (e.g. 'OPS-12')."""
    resp = await _get_client().get(f"/rest/api/2/issue/{key}")
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def create_issue(summary: str, cmdb_ci: str, priority: str = "P3") -> dict:
    """Create a new tracker issue against a CI."""
    resp = await _get_client().post("/rest/api/2/issue", json={"summary": summary, "cmdb_ci": cmdb_ci, "priority": priority})
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def link_issue(source_key: str, target_key: str, link_type: str = "relates to") -> dict:
    """Link two tracker issues (e.g. incident -> follow-up tuning task)."""
    resp = await _get_client().post(f"/rest/api/2/issueLink?source_key={source_key}", json={"target_key": target_key, "link_type": link_type})
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def transition_issue(key: str, transition_id: str) -> dict:
    """Transition an issue's workflow state (1=In Progress, 2=Done, 3=Open)."""
    resp = await _get_client().post(f"/rest/api/2/issue/{key}/transitions", json={"transition_id": transition_id})
    resp.raise_for_status()
    return resp.json()


async def _self_test() -> None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    import mcp_servers.simulators.tracker as sim_module

    global _client
    _client = httpx.AsyncClient(transport=httpx.ASGITransport(app=sim_module.app), base_url="http://sim")

    result = await create_issue(summary="MCP test issue", cmdb_ci="CI-0001")
    key = result["key"]
    print(f"PASS create_issue (via MCP tool): {key}")

    result = await get_issue(key=key)
    assert result["key"] == key
    print(f"PASS get_issue (via MCP tool): {key}")

    result = await transition_issue(key=key, transition_id="1")
    assert result["fields"]["status"]["name"] == "In Progress"
    print(f"PASS transition_issue (via MCP tool): {key} -> In Progress")

    sim_module._seed_store()
    target_key = next(iter(sim_module._STORE))
    result = await link_issue(source_key=key, target_key=target_key)
    assert len(result["links"]) == 1
    print(f"PASS link_issue (via MCP tool): {key} -> {target_key}")

    await _client.aclose()
    print("\nSELF-TEST PASSED: Tracker MCP tools work end to end against the simulator (in-process).")


if __name__ == "__main__":
    if "--test" in sys.argv:
        import asyncio

        asyncio.run(_self_test())
    else:
        mcp.run(transport="stdio")
