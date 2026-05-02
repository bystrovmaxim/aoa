# src/examples/fastapi_mcp_services/infrastructure.py
"""
Shared ActionMachine runtime wiring for the FastAPI and MCP example apps.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``ActionProductMachine`` and ``NoAuthCoordinator`` are constructed once and
imported by both transports so HTTP and MCP share the same runtime instance and
auth policy.

``ActionProductMachine`` creates its default ``NodeGraphCoordinator`` lazily.
Adapters receive ``machine`` and ``auth``; they use ``machine.graph_coordinator``
when they need the graph.

``NoAuthCoordinator`` states that this sample performs no real authentication.
For production, supply an ``AuthCoordinator`` with ``CredentialExtractor``,
``Authenticator``, and ``ContextAssembler``. Keep ``NoAuthCoordinator`` only
for intentionally public APIs.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    infrastructure (this module)
    +-- machine = ActionProductMachine(mode="production")
    |       +-- built NodeGraphCoordinator (lazy factory inside machine)
    +-- auth    = NoAuthCoordinator()
              |
              +------------------+------------------+
              |                                     |
      app_fastapi_service                   app_mcp_service
      FastApiAdapter(machine, auth)         McpAdapter(machine, auth)
              |                                     |
              v                                     v
        HTTP routes                          MCP tools
              \\___________________________________/
                    same machine + auth instances

"""

from action_machine.auth.auth_coordinator import NoAuthCoordinator
from action_machine.runtime.action_product_machine import ActionProductMachine

machine = ActionProductMachine(mode="production")
auth = NoAuthCoordinator()
