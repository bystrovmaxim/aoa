"""
01_tool.py — Publish Actions as MCP tools with McpAdapter

The same Action that serves HTTP also becomes a tool for an AI agent — no logic
duplicated, no rewrite for another protocol. The adapter derives the tool's input
schema from Params, the description from @meta, and a handler that delegates to
machine.run(). Every call returns a JSON envelope wrapped in a CallToolResult:
success -> {"ok": true, "code": "OK", "data": ...}; failures ->
{"ok": false, "code": "PERMISSION_DENIED" | "INVALID_PARAMS" | "INTERNAL_ERROR", ...}.

This example calls the built FastMCP server in-process (server.call_tool), so it
runs without an MCP client or LLM. In production you serve the returned server.

Tutorial: ../../docs/tutorials/step-14-mcp_draft.md  ·  topic: MCP adapter

Run:
    uv run python examples/step_14_mcp/01_tool.py
"""

import asyncio

from mcp.server.fastmcp.exceptions import ToolError
from pydantic import Field

from aoa.action_machine.auth import ApplicationRole, GuestRole, NoAuthCoordinator
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.mcp import McpAdapter


class GreetingDomain(BaseDomain):
    name = "greeting"
    description = "Greetings domain"


class AdminRole(ApplicationRole):
    name = "admin"
    description = "Administrator"


class GreetParams(BaseParams):
    name: str = Field(description="Person to greet")


class GreetResult(BaseResult):
    message: str = Field(description="Greeting message")


# ── Open operation: any agent may call it ────────────────────────────────────
@meta(description="Greet a person by name", domain=GreetingDomain)
@check_roles(GuestRole)
class GreetAction(BaseAction[GreetParams, GreetResult]):

    @summary_aspect("Build greeting")
    async def greet_summary(self, params, state, box, connections):
        return GreetResult(message=f"Hello, {params.name}!")


# ── Protected operation: anonymous agent is rejected with PERMISSION_DENIED ──
@meta(description="Admin-only ping", domain=GreetingDomain)
@check_roles(AdminRole)
class AdminPingAction(BaseAction[GreetParams, GreetResult]):

    @summary_aspect("Admin ping")
    async def ping_summary(self, params, state, box, connections):
        return GreetResult(message=f"pong for {params.name}")


def build_server():
    machine = ActionProductMachine()
    return (
        McpAdapter(machine=machine, auth_coordinator=NoAuthCoordinator(context=Context()), server_name="Greetings MCP")
        .tool("greetings.greet", GreetAction)
        .tool("greetings.admin_ping", AdminPingAction)
        .build()
    )


def envelope(result) -> str:
    """Format a CallToolResult as `isError=… <json text>`."""
    content = getattr(result, "content", result)
    block = content[0] if isinstance(content, (list, tuple)) else content
    text = getattr(block, "text", str(block))
    return f"isError={getattr(result, 'isError', None)}  {text}"


async def main() -> None:
    server = build_server()

    tools = await server.list_tools()
    print("Tools exposed to the agent:")
    for t in tools:
        print(f"  {t.name:22} inputSchema.required={t.inputSchema.get('required')}")

    print("\nCalls:")
    r = await server.call_tool("greetings.greet", {"name": "Alice"})
    print(f"  greet(name=Alice)      -> {envelope(r)}")

    r = await server.call_tool("greetings.admin_ping", {"name": "Alice"})
    print(f"  admin_ping(name=Alice) -> {envelope(r)}")

    # A malformed call is rejected by the inputSchema at the protocol boundary,
    # before the handler runs — the agent gets a protocol-level error.
    try:
        await server.call_tool("greetings.greet", {})  # missing required `name`
    except ToolError:
        print("  greet()  [no name]     -> ToolError: inputSchema rejected the call ('name' is required)")


if __name__ == "__main__":
    asyncio.run(main())
