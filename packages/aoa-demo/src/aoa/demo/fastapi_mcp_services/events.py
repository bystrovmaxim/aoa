# packages/aoa-demo/src/aoa/demo/fastapi_mcp_services/events.py
"""
Order events — the facts of the orders domain.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The vocabulary of ``OrdersDomain``. Each action declares the event it emits with
``@emits``, and the domain lists them in ``events``.
"""

from aoa.action_machine.model.base_event import BaseEvent


class OrderRequestedEvent(BaseEvent):
    """Someone asked for an order."""

    order_id: str


class OrderValidatedEvent(BaseEvent):
    """An order's input was accepted."""

    user_id: str
    amount: float
