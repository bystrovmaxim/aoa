# packages/aoa-mcp-adapter/tests/test_adapter_lifespan.py
"""
The MCP adapter's one lifecycle option: a server's startup and shutdown.

An MCP service has no request-scoped startup hook of its own, but the server it
builds has one: ``FastMCP`` takes a lifespan context manager, and the adapter
hands the application's through untouched. This is where a process-wide pool is
created and closed for a service that never sees an ASGI request.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    adapter.build(lifespan=…)  ──>  FastMCP(…, lifespan=…)
                                        │
                              server.settings.lifespan ──> the application's own object

"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

from mcp.server.fastmcp import FastMCP

from aoa.action_machine.context.context import Context
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.mcp.adapter import McpAdapter


def _make_adapter() -> McpAdapter:
    """Build the smallest adapter that can produce a server."""
    machine = ActionProductMachine(loggers=[])
    auth = AsyncMock()
    auth.process.return_value = Context()
    return McpAdapter(machine=machine, auth_coordinator=auth, server_name="Lifespan test")


def test_an_absent_option_leaves_the_server_with_no_lifespan() -> None:
    """Building with no lifecycle option keeps the server exactly as it was."""
    server = _make_adapter().build()

    assert server.settings.lifespan is None


async def test_the_option_reaches_fastmcp_and_runs() -> None:
    """The server holds the application's own context manager, and entering it starts it."""
    events: list[str] = []

    @asynccontextmanager
    async def lifespan(server: FastMCP) -> AsyncIterator[None]:
        events.append("started")
        try:
            yield
        finally:
            events.append("closed")

    server = _make_adapter().build(lifespan=lifespan)

    assert server.settings.lifespan is lifespan

    async with server.settings.lifespan(server):
        assert events == ["started"]

    assert events == ["started", "closed"]
