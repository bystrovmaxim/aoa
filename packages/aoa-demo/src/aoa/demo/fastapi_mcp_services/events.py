# packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/events.py
"""
Order events — the facts of the orders domain.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The vocabulary of ``OrdersDomain``. Each action declares the event it emits with
``@emits``, and the domain lists them in ``events``.
"""

from pydantic import Field

from aoa.action_machine.model.base_event import BaseEvent


class OrderRequestedEvent(BaseEvent):
    """Someone asked for an order."""

    order_id: str = Field(description="The order that was asked for")


class OrderValidatedEvent(BaseEvent):
    """An order's input was accepted."""

    user_id: str = Field(description="Who placed the order")
    amount: float = Field(description="The order total")
