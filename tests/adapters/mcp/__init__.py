# tests/adapters/mcp/__init__.py
"""
Tests for the MCP integration layer.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exercise ``McpAdapter`` (tool registration, ``build()``, fluent chain,
``register_all()``, ``system://graph`` resource, error surfaces) and
``McpRouteRecord`` (tool name validation, defaults, type extraction).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    MCP client / handler tests
              |
              v
         McpAdapter.build()
              |
              v
    machine.run + coordinator graph (schema / graph JSON)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Tool names must stay non-empty and normalized per ``McpRouteRecord`` rules.
- Graph JSON tests assert stable keys (``nodes``, ``edges``, ``source_key``, …).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uv run pytest tests/adapters/mcp/ -q

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Handler tests rely on MCP SDK types; version bumps may require fixture tweaks.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: MCP adapter test subpackage.
CONTRACT: Tools, records, schemas, and graph resource behavior.
INVARIANTS: Shared scenario actions; mocks for protocol surfaces.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""
