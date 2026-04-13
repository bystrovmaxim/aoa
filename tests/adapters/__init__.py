# tests/adapters/__init__.py
"""
Tests for the ActionMachine adapter layer.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers ``BaseAdapter``, ``BaseRouteRecord``, ``extract_action_types``, and the
concrete integrations: ``FastApiAdapter`` (HTTP) and ``McpAdapter`` (MCP tools).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseRouteRecord / extract_action_types
              |
              v
    BaseAdapter (shared contract)
              |
      +-------+--------+
      |                |
 FastApiAdapter    McpAdapter
      |                |
      v                v
  HTTP tests       MCP tests
  (fastapi/)       (mcp/)

Test modules:
    test_base_adapter.py        — ``BaseAdapter`` construction, properties,
                                  ``_add_route`` fluent API, abstract ``build()``.
    test_base_route_record.py — ``BaseRouteRecord`` guards, ``action_class``
                                  validation, type extraction, mapper invariants,
                                  ``effective_*_model`` properties.
    fastapi/
        test_fastapi_adapter.py       — registration, ``build()``, fluent chain,
                                        health route, exception handlers.
        test_fastapi_route_record.py  — HTTP validation (method, path), defaults,
                                        normalization.
        test_fastapi_endpoints.py     — endpoint strategies (body vs query vs none).
        test_fastapi_mapper_guards.py — mapper / model guard rails.
        test_fastapi_openapi.py       — OpenAPI shape for registered routes.
    mcp/
        test_mcp_adapter.py           — tool registration, ``build()``, fluent chain,
                                        ``register_all()``, ``system://graph``.
        test_mcp_route_record.py      — MCP validation (``tool_name``), defaults.
        test_mcp_schema.py            — ``inputSchema`` from Params models.
        test_mcp_handler.py           — handler wiring and graph JSON.

Domain actions come from ``tests.scenarios.domain_model``. Deliberately broken
actions (missing ``@meta``, bad generics) live inside individual test files as
local helpers — not part of the shared domain.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Adapter tests use real coordinator/machine patterns or focused mocks; no import
  from production ``examples`` packages unless a test explicitly needs them.
- Route records must always validate ``action_class`` before type extraction.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uv run pytest tests/adapters/ -q

Edge case: transport-specific extras (FastAPI, MCP) must be installed for the
corresponding subfolder tests to import integration modules.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Tests mirror adapter implementation details (line references in module docs may
  drift after refactors — treat as hints, not contracts).

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Test package boundary for HTTP and MCP adapter integrations.
CONTRACT: Exercise public adapter APIs and route-record type resolution.
INVARIANTS: Shared domain actions; local broken fixtures only inside tests.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""
