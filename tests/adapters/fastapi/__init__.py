# tests/adapters/fastapi/__init__.py
"""
Tests for the FastAPI integration layer.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Exercise ``FastApiAdapter`` (route registration, ``build()``, fluent chain, health
check, exception handlers, OpenAPI metadata), ``FastApiRouteRecord`` (HTTP-specific
validation and defaults), and OpenAPI output for registered routes.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    TestClient  ->  Starlette/FastAPI app  <-  FastApiAdapter.build()
                           |
                           v
                    mocked or real machine.run
                           |
                           v
                    domain actions (scenarios)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Auth coordinator is always provided to ``FastApiAdapter`` (often ``AsyncMock``).
- Endpoint strategy tests live in ``test_fastapi_endpoints.py`` separately from
  adapter smoke tests.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uv run pytest tests/adapters/fastapi/ -q

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Some tests pin internal helper names (e.g. ``_make_endpoint_with_query``) as
  documentation anchors; update comments if implementation moves.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: FastAPI adapter test subpackage.
CONTRACT: Cover registration, HTTP semantics, and OpenAPI surfaces.
INVARIANTS: No duplicate domain actions — reuse ``tests.scenarios.domain_model``.
═══════════════════════════════════════════════════════════════════════════════
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""
