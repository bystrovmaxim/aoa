# tests/adapters/mcp/__init__.py
"""
Tests for the MCP adapter layer.

Covers McpAdapter (tool registration, build, fluent chain, register_all,
system://graph resource, error handling) and McpRouteRecord (MCP-specific
validation, field defaults).

Test modules:
    test_mcp_adapter.py       — Adapter construction, tool() registration,
                                build() producing a FastMCP server, fluent
                                chaining, register_all() auto-registration,
                                snake_case tool naming, error string formats.
    test_mcp_route_record.py  — MCP-specific validation (tool_name non-empty),
                                field defaults, inherited BaseRouteRecord
                                invariants.
    test_mcp_schema.py        — inputSchema generation from Params models
                                via model_json_schema(), field descriptions,
                                constraints, required fields.
"""
