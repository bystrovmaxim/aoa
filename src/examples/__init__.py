# src/examples/__init__.py
"""
Usage examples for ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Demonstrate end-to-end wiring (e.g. FastAPI + MCP with shared actions) without
shipping example code inside the core ``action_machine`` package. Actions use
standard **Intent** mixins on ``BaseAction`` and decorators for metadata and
pipeline behavior. See the repository root ``README.md`` (Intent / architecture
sections) and ``docs/CHANGELOG.md`` for naming and API notes.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    action_machine (library)
              ^
              | imports only from here as a separate namespace
              |
    examples/  (this package)
              |
              +-- fastapi_mcp_services/
              |       dual-transport app + shared actions
              |
              +-- (future example packages)

    Consumers typically copy or study subpackages; the library does not depend
    on ``examples`` at runtime.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Start with the dual-transport demo::

    # See src/examples/fastapi_mcp_services/README.md
    # Run FastAPI: uvicorn examples.fastapi_mcp_services.app_fastapi_service:app
    # Run MCP:     python -m examples.fastapi_mcp_services.app_mcp_service

Edge case: importing ``examples`` alone does not start servers or register routes;
open the subpackage README for commands and dependencies.
"""
