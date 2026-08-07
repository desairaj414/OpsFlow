"""MCP server wrapping the CMDB simulator — exposes the typed tool set from api-contract.md
("CMDB: get_ci(id), get_relationships(ci_id), propose_ci_update") over MCP, per PRD §3.8.
propose_ci_update stays a proposal at this layer too — it never writes the CI directly; a human
approval step (not yet built) is what would apply it.

    python mcp_servers/cmdb_mcp.py         # runs the MCP server (stdio transport)
    python mcp_servers/cmdb_mcp.py --test  # in-process self-test (ASGI transport, no real port)
"""
import os
import sys

import httpx
from mcp.server.fastmcp import FastMCP

SIMULATOR_BASE_URL = os.getenv("CMDB_SIM_URL", "http://localhost:9004")

mcp = FastMCP("cmdb")
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=SIMULATOR_BASE_URL)
    return _client


@mcp.tool()
async def get_ci(ci_id: str) -> dict:
    """Get a single Configuration Item by id."""
    resp = await _get_client().get(f"/cmdb_ci/{ci_id}")
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def get_relationships(ci_id: str) -> dict:
    """Get a CI's outgoing relationships (depends_on, hosts, connects_to, replicates_to)."""
    resp = await _get_client().get(f"/cmdb_ci/{ci_id}/relationships")
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def propose_ci_update(ci_id: str, field: str, proposed_value: str, reason: str, actor: str) -> dict:
    """Propose a CI field update. Does NOT write the CI — human approval required before any write."""
    resp = await _get_client().post(f"/cmdb_ci/{ci_id}/propose_update", json={
        "field": field, "proposed_value": proposed_value, "reason": reason, "actor": actor,
    })
    resp.raise_for_status()
    return resp.json()


async def _self_test() -> None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    import mcp_servers.simulators.cmdb as sim_module

    global _client
    _client = httpx.AsyncClient(transport=httpx.ASGITransport(app=sim_module.app), base_url="http://sim")

    result = await get_ci(ci_id="CI-0001")
    assert result["id"] == "CI-0001"
    print(f"PASS get_ci (via MCP tool): {result['id']} ({result['type']})")

    result = await get_relationships(ci_id="CI-0001")
    print(f"PASS get_relationships (via MCP tool): {len(result['relationships'])} relationships")

    result = await propose_ci_update(ci_id="CI-0001", field="patch_level", proposed_value="9.9.9", reason="MCP test", actor="smoke-test")
    assert result["status"] == "pending_approval"
    print(f"PASS propose_ci_update (via MCP tool): {result['proposal_id']} (status={result['status']})")

    result = await get_ci(ci_id="CI-0001")
    assert result["patch_level"] != "9.9.9", "propose_ci_update must not mutate the CI directly"
    print("PASS propose_ci_update did not mutate the CI (human-approval gate intact)")

    await _client.aclose()
    print("\nSELF-TEST PASSED: CMDB MCP tools work end to end against the simulator (in-process).")


if __name__ == "__main__":
    if "--test" in sys.argv:
        import asyncio

        asyncio.run(_self_test())
    else:
        mcp.run(transport="stdio")
