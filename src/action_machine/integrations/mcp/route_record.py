# src/action_machine/integrations/mcp/route_record.py
"""
McpRouteRecord — frozen route record for MCP adapter.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Concrete ``BaseRouteRecord`` subtype for MCP transport metadata.
Stores one MCP tool contract used by ``McpAdapter.build()``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    McpAdapter.tool(...)
            |
            v
    McpRouteRecord(
      action + mapping + tool metadata
    )
            |
            v
    McpAdapter.build() -> MCP Tool

═══════════════════════════════════════════════════════════════════════════════
MCP-SPECIFIC FIELDS
═══════════════════════════════════════════════════════════════════════════════

- ``tool_name``: MCP tool identifier visible to agents. Recommended format:
  ``domain.action`` (for example: ``orders.create``).
- ``description``: human-readable tool description for agent tool selection.
  If empty, adapter may fill it from action ``@meta``.

Mapper naming convention:
    params_mapper   -> returns params   (request -> params)
    response_mapper -> returns response (result  -> response)

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # Minimal:
    record = McpRouteRecord(
        action_class=CreateOrderAction,
        tool_name="orders.create",
    )

    # Full:
    record = McpRouteRecord(
        action_class=CreateOrderAction,
        request_model=CreateOrderRequest,
        response_model=CreateOrderResponse,
        params_mapper=map_request_to_params,
        response_mapper=map_result_to_response,
        tool_name="orders.create",
        description="Create a new order in the system",
    )

    # Edge case: invalid empty name.
    # McpRouteRecord(action_class=CreateOrderAction, tool_name="  ") -> ValueError
"""

from __future__ import annotations

from dataclasses import dataclass

from action_machine.adapters.base_route_record import BaseRouteRecord


@dataclass(frozen=True)
class McpRouteRecord(BaseRouteRecord):
    """
AI-CORE-BEGIN
    ROLE: Carries validated tool metadata and mapping contracts.
    CONTRACT: Extends BaseRouteRecord with MCP-specific fields.
    INVARIANTS: Frozen instance and non-empty tool_name.
    AI-CORE-END
"""

    # ── MCP-specific fields ─────────────────────────────────────────────

    tool_name: str = ""
    description: str = ""

    # ── Validation ──────────────────────────────────────────────────────

    def __post_init__(self) -> None:
        """
        Validate MCP-specific invariants after construction.

        Order:
        1. Call ``super().__post_init__()`` for BaseRouteRecord invariants.
        2. Validate non-empty ``tool_name`` after ``strip()``.

        Raises:
            TypeError: propagated from BaseRouteRecord.
            ValueError: propagated from BaseRouteRecord or empty ``tool_name``.
        """
        # ── 1. BaseRouteRecord invariants ──
        super().__post_init__()

        # ── 2. tool_name validation ──
        if not self.tool_name or not self.tool_name.strip():
            raise ValueError(
                "tool_name cannot be empty. "
                "Provide a tool identifier, for example 'orders.create'."
            )
