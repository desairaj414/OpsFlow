"""MCP server wrapping the ITSM simulator — exposes the typed tool set from api-contract.md
("ITSM: create_ticket, update_ticket, add_work_note, get_ticket(sys_id)") over MCP, per PRD §3.8.

    python mcp_servers/itsm_mcp.py         # runs the MCP server (stdio transport)
    python mcp_servers/itsm_mcp.py --test  # in-process self-test (ASGI transport, no real port)
"""
import os
import sys

import httpx
from mcp.server.fastmcp import FastMCP

SIMULATOR_BASE_URL = os.getenv("ITSM_SIM_URL", "http://localhost:9002")

mcp = FastMCP("itsm")
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(base_url=SIMULATOR_BASE_URL)
    return _client


@mcp.tool()
async def get_ticket(sys_id: str) -> dict:
    """Get a single ITSM ticket by sys_id."""
    resp = await _get_client().get(f"/api/now/table/incident/{sys_id}")
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def create_ticket(short_description: str, priority: str, cmdb_ci: str, sys_class_name: str = "incident") -> dict:
    """Create a new ITSM ticket against a CI."""
    resp = await _get_client().post("/api/now/table/incident", json={
        "short_description": short_description, "priority": priority,
        "cmdb_ci": cmdb_ci, "sys_class_name": sys_class_name,
    })
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def update_ticket(sys_id: str, state: str | None = None, priority: str | None = None) -> dict:
    """Update a ticket's state and/or priority."""
    resp = await _get_client().patch(f"/api/now/table/incident/{sys_id}", json={"state": state, "priority": priority})
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def add_work_note(sys_id: str, note: str, actor: str) -> dict:
    """Append a work note to a ticket, attributed to actor."""
    resp = await _get_client().post(f"/api/now/table/incident/{sys_id}/work_notes", json={"note": note, "actor": actor})
    resp.raise_for_status()
    return resp.json()


async def _self_test() -> None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    import mcp_servers.simulators.itsm as sim_module

    global _client
    _client = httpx.AsyncClient(transport=httpx.ASGITransport(app=sim_module.app), base_url="http://sim")

    result = await create_ticket(short_description="MCP test ticket", priority="P2", cmdb_ci="CI-0001")
    sys_id = result["result"]["sys_id"]
    print(f"PASS create_ticket (via MCP tool): {sys_id}")

    result = await get_ticket(sys_id=sys_id)
    assert result["result"]["sys_id"] == sys_id
    print(f"PASS get_ticket (via MCP tool): {sys_id}")

    result = await update_ticket(sys_id=sys_id, state="7")
    assert result["result"]["closed_at"] is not None
    print(f"PASS update_ticket (via MCP tool): {sys_id} closed")

    result = await add_work_note(sys_id=sys_id, note="closed via MCP test", actor="smoke-test")
    assert len(result["result"]["work_notes"]) == 1
    print(f"PASS add_work_note (via MCP tool): {sys_id}")

    await _client.aclose()
    print("\nSELF-TEST PASSED: ITSM MCP tools work end to end against the simulator (in-process).")


if __name__ == "__main__":
    if "--test" in sys.argv:
        import asyncio

        asyncio.run(_self_test())
    else:
        mcp.run(transport="stdio")
