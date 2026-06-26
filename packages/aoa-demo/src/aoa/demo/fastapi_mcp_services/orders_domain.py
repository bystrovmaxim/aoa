# packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/orders_domain.py
"""OrdersDomain — order lifecycle grouping for FastAPI + MCP demos."""

from aoa.action_machine.domain import BaseDomain


class OrdersDomain(BaseDomain):
    """Order lifecycle actions (create, fetch, etc.)."""

    name = "orders"
    description = "Order lifecycle and lookup."
