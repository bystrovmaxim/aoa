# packages/aoa-demo/tests/fastapi_mcp_services/test_order_events.py
"""
The orders domain speaks in typed events, and the product behaves as it did.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Proves the whole cascade on the demo: the two lines keep their text, the answers stay,
a line with ``kwargs`` is refused, and the build holds ``@emits`` to the vocabulary.
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions.event_contract_error import EventContractError
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.emission_rules import emission_rules_for
from aoa.demo.fastapi_mcp_services.actions.create_order import CreateOrderAction
from aoa.demo.fastapi_mcp_services.actions.get_order import GetOrderAction
from aoa.demo.fastapi_mcp_services.events import OrderRequestedEvent, OrderValidatedEvent
from aoa.demo.fastapi_mcp_services.orders_domain import OrdersDomain


class _RecordingLogger(BaseLogger):
    """A logger keeping the text and ``var`` of every line."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[tuple[str, Any]] = []

    async def write(self, scope: Any, message: str, var: Any, ctx: Any, state: Any, params: Any, indent: int) -> None:
        """Keep one line."""
        self.lines.append((message, var))


@pytest.fixture
def logger() -> _RecordingLogger:
    return _RecordingLogger()


@pytest.fixture
def machine(logger: _RecordingLogger) -> ActionProductMachine:
    return ActionProductMachine(cache_coordinator=None, log_coordinator=LogCoordinator(loggers=[logger]))


async def test_get_order_delivers_its_event_with_the_same_text(
    machine: ActionProductMachine, logger: _RecordingLogger
) -> None:
    result = await machine.run(Context(), GetOrderAction(), GetOrderAction.Params(order_id="o1"))

    assert (result.order_id, result.status, result.total) == ("o1", "created", 1500.0)
    message, var = logger.lines[0]
    assert message == "Order request: o1"
    assert var.model_dump() == {"order_id": "o1"}
    assert isinstance(var, OrderRequestedEvent)


async def test_create_order_delivers_its_event_with_the_same_text(
    machine: ActionProductMachine, logger: _RecordingLogger
) -> None:
    context = Context(user=UserInfo(user_id="u1"))
    params = CreateOrderAction.Params(user_id="u1", amount=10.0, currency="USD")

    await machine.run(context, CreateOrderAction(), params)

    message, var = logger.lines[0]
    assert message == "Order validation: user=u1, amount=10.0"
    assert isinstance(var, OrderValidatedEvent)


def test_the_domain_lists_both_events() -> None:
    assert set(OrdersDomain.events) == {OrderRequestedEvent, OrderValidatedEvent}


def test_a_declared_event_removed_from_the_domain_fails_the_build(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(OrdersDomain, "events", (OrderRequestedEvent,))

    with pytest.raises(EventContractError, match="OrderValidatedEvent"):
        create_node_graph_coordinator()


def test_a_line_with_kwargs_in_the_domain_is_refused() -> None:
    rules = emission_rules_for(GetOrderAction, "get_order_summary")

    assert rules is not None
    with pytest.raises(EventContractError):
        rules.check(None)
