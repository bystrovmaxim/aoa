# src/examples/fastapi_mcp_services/infrastructure.py
r"""
Shared ActionMachine runtime wiring for the FastAPI and MCP example apps.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``ActionProductMachine`` and ``NoAuthCoordinator`` are constructed once and
imported by both transports so HTTP and MCP share the same runtime instance and
auth policy.

``ActionProductMachine`` creates a **built** ``GraphCoordinator`` internally
(see ``ActionProductMachine.create_default_coordinator()``) unless you pass a
custom ``coordinator=`` at construction time. Adapters receive only ``machine``
and ``auth``; they read ``machine.gate_coordinator`` when they need the graph.

``NoAuthCoordinator`` states that this sample performs no real authentication.
For production, supply an ``AuthCoordinator`` with ``CredentialExtractor``,
``Authenticator``, and ``ContextAssembler``. Keep ``NoAuthCoordinator`` only
for intentionally public APIs.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    infrastructure (this module)
    +-- machine = ActionProductMachine(mode="production")
    |       +-- built GraphCoordinator (default factory inside machine)
    +-- auth    = NoAuthCoordinator()
              |
              +------------------+------------------+
              |                                     |
      app_fastapi_service                   app_mcp_service
      FastApiAdapter(machine, auth)         McpAdapter(machine, auth)
              |                                     |
              v                                     v
        HTTP routes                          MCP tools
              \___________________________________/
                    same machine + auth instances

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Do not construct a second ``ActionProductMachine`` per transport in this
  pattern; reuse the module-level ``machine`` (and ``auth``).
- ``mode="production"`` is an example choice, not a deployment guarantee.
- Adapters require ``auth_coordinator`` even when it is ``NoAuthCoordinator``.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from examples.fastapi_mcp_services.infrastructure import auth, machine

    # app_fastapi_service / app_mcp_service pass these into adapters.

    Edge case: custom ``GraphCoordinator`` — pass
    ``ActionProductMachine(..., coordinator=my_coordinator)`` here; it must
    already be ``.build()`` complete.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Example-only bootstrap, not a full DI layer or multi-tenant configuration.
- Unbuilt coordinators passed into ``ActionProductMachine`` raise at init.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Shared machine + auth singletons for dual-transport example.
CONTRACT: Export ``machine`` and ``auth`` for adapter construction.
INVARIANTS: Single machine instance; coordinator owned by machine unless injected.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from action_machine.intents.auth import NoAuthCoordinator
from action_machine.runtime.machines.action_product_machine import ActionProductMachine

machine = ActionProductMachine(mode="production")
auth = NoAuthCoordinator()
