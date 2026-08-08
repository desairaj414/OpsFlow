"""MCP server wrapping the patch-source simulator — exposes get_pending_patches(ci_id) and
get_change_calendar(scope) over MCP, same shape as cmdb_mcp.py/itsm_mcp.py (api-contract.md, PRD
§3.8). This is the "go to the sites for patches" lookup Enrichment/Planner call for patch workflows
— same simulated-system pattern every other MCP tool in this app already uses, not a real network
call to a vendor site.

    python mcp_servers/patch_mcp.py         # runs the MCP server (stdio transport)
    python mcp_servers/patch_mcp.py --test  # in-process self-test (ASGI transport, no real port)
"""
import os
import sys

import httpx
from mcp.server.fastmcp import FastMCP

SIMULATOR_BASE_URL = os.getenv("PATCH_SIM_URL", "http://localhost:9005")

mcp = FastMCP("patch_source")
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=SIMULATOR_BASE_URL)
    return _client


@mcp.tool()
async def get_pending_patches(ci_id: str) -> dict:
    """Get the pending vendor patches for a CI (severity, CVE ids, dependency ordering)."""
    resp = await _get_client().get(f"/patch_inventory/{ci_id}")
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def get_change_calendar(scope: str) -> dict:
    """Get blackout/freeze windows for a scope ('global' windows are always included alongside it)."""
    resp = await _get_client().get("/change_calendar", params={"scope": scope})
    resp.raise_for_status()
    return resp.json()


async def _self_test() -> None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    import mcp_servers.simulators.patch_source as sim_module

    global _client
    _client = httpx.AsyncClient(transport=httpx.ASGITransport(app=sim_module.app), base_url="http://sim")

    result = await get_pending_patches(ci_id="CI-0059")
    assert result["ci_id"] == "CI-0059"
    assert len(result["patches"]) >= 1
    print(f"PASS get_pending_patches (via MCP tool): {len(result['patches'])} pending patch(es) for CI-0059")

    result = await get_change_calendar(scope="prod")
    assert any(w["scope"] == "global" for w in result["blackouts"])
    print(f"PASS get_change_calendar (via MCP tool): {len(result['blackouts'])} window(s) for scope=prod")

    await _client.aclose()
    print("\nSELF-TEST PASSED: Patch MCP tools work end to end against the simulator (in-process).")


if __name__ == "__main__":
    if "--test" in sys.argv:
        import asyncio

        asyncio.run(_self_test())
    else:
        mcp.run(transport="stdio")
