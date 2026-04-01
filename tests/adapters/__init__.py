# tests/adapters/__init__.py
"""
Tests for the adapter layer of ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers BaseAdapter, BaseRouteRecord, extract_action_types, and the two
concrete adapters: FastApiAdapter (HTTP) and McpAdapter (MCP tools).

Test modules:
    test_base_adapter.py        — BaseAdapter constructor validation, properties,
                                  _add_route fluent API, build() abstractness.
    test_base_route_record.py   — BaseRouteRecord instantiation guard, action_class
                                  validation, type extraction, mapper invariants,
                                  computed properties (params_type, result_type,
                                  effective_request_model, effective_response_model).
    fastapi/
        test_fastapi_adapter.py       — FastApiAdapter registration, build(), fluent
                                        chain, health check, exception handlers.
        test_fastapi_route_record.py  — FastApiRouteRecord HTTP-specific validation
                                        (method, path), field defaults, normalization.
        test_fastapi_openapi.py       — OpenAPI schema generation from registered routes.
    mcp/
        test_mcp_adapter.py           — McpAdapter tool registration, build(), fluent
                                        chain, register_all(), system://graph resource.
        test_mcp_route_record.py      — McpRouteRecord MCP-specific validation
                                        (tool_name), field defaults.
        test_mcp_schema.py            — inputSchema generation from Params models.

Domain actions used in tests are imported from tests.domain. Intentionally
broken actions (missing @meta, wrong generics) are defined inside test files
as edge-case helpers — they do not belong to the shared domain model.
"""
