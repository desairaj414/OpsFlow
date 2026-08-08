"""Shared MCP client wiring for agents/tests/scripts — same in-process ASGI transport pattern each
mcp_servers/*_mcp.py uses for its own --test, factored out so every Phase 3 agent doesn't repeat it.
Production would instead point each *_mcp module's client at the real running simulator port
(9001-9004); this wiring is for in-process use (tests, the gate script, agent dev-time runs).
"""
import httpx

import mcp_servers.cmdb_mcp as cmdb_mcp
import mcp_servers.itsm_mcp as itsm_mcp
import mcp_servers.monitoring_mcp as monitoring_mcp
import mcp_servers.patch_mcp as patch_mcp
import mcp_servers.simulators.cmdb as cmdb_sim
import mcp_servers.simulators.itsm as itsm_sim
import mcp_servers.simulators.monitoring as monitoring_sim
import mcp_servers.simulators.patch_source as patch_sim
import mcp_servers.simulators.tracker as tracker_sim
import mcp_servers.tracker_mcp as tracker_mcp

_WIRED = False


def wire_all_in_process() -> None:
    """Idempotent — safe to call from every agent module/test without re-wiring repeatedly."""
    global _WIRED
    if _WIRED:
        return
    for mcp_module, sim_module in (
        (monitoring_mcp, monitoring_sim),
        (itsm_mcp, itsm_sim),
        (tracker_mcp, tracker_sim),
        (cmdb_mcp, cmdb_sim),
        (patch_mcp, patch_sim),
    ):
        mcp_module._client = httpx.AsyncClient(transport=httpx.ASGITransport(app=sim_module.app), base_url="http://sim")
    _WIRED = True
