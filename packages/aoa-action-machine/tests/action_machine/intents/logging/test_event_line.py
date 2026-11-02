# packages/aoa-action-machine/tests/action_machine/intents/logging/test_event_line.py
"""
A line with an event — what a logger receives, and what a call refuses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The event takes the place of ``kwargs`` and the text stays the author's template. These
tests hold with no switch on: nothing here depends on ``@emits`` or ``events``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.event_contract_error import EventContractError
from aoa.action_machine.exceptions.log_template_error import LogTemplateError
from aoa.action_machine.logging import sensitive
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.channel import Channel
from aoa.action_machine.logging.level import Level
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.logging.log_scope import LogScope
from aoa.action_machine.logging.scoped_logger import ScopedLogger
from aoa.action_machine.model import BaseParams, BaseSchema, BaseState
from aoa.action_machine.model.base_event import BaseEvent
from aoa.action_machine.runtime.tools_box import ToolsBox

TOOLS = (("info", Level.info), ("warning", Level.warning), ("critical", Level.critical))


class ShopDomain(BaseDomain):
    """A domain for the lines of these tests."""

    name = "shop"
    description = "Shop"


class ItemSchema(BaseSchema):
    """A nested value."""

    name: str


class OrderCompletedEvent(BaseEvent):
    """A fact with a nested value and a masked property."""

    order_id: str
    total: float
    item: ItemSchema
    card: str

    @property
    @sensitive(True, max_chars=2, char="*", max_percent=100)
    def card_shown(self) -> str:
        """The card, masked in a rendered line."""
        return self.card


@dataclass(frozen=True)
class _Line:
    """One written line."""

    message: str
    var: Any


class _RecordingLogger(BaseLogger):
    """A logger keeping every line."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[_Line] = []

    async def write(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        indent: int,
    ) -> None:
        """Keep one line."""
        self.lines.append(_Line(message, var))


def _event() -> OrderCompletedEvent:
    """Build the event of these tests."""
    return OrderCompletedEvent(order_id="o1", total=9.5, item=ItemSchema(name="pen"), card="4111222233334444")


def _box(logger: BaseLogger) -> ToolsBox:
    """Return a box that writes to ``logger``."""
    log = ScopedLogger(
        coordinator=LogCoordinator([logger]),
        nest_level=0,
        action_name="ShopAction",
        aspect_name="pay_aspect",
        context=Context(),
        state=BaseState(paid=True),
        params=BaseParams(),
        domain=ShopDomain,
    )
    return ToolsBox(run_child=MagicMock(), resources=None, log=log, nested_level=0, factory=MagicMock())


@pytest.mark.parametrize(("tool", "level"), TOOLS)
async def test_a_line_with_an_event(tool: str, level: Level) -> None:
    logger = _RecordingLogger()
    event = _event()

    await getattr(_box(logger), tool)(Channel.business, "Order {%var.order_id}", event)

    line = logger.lines[0]
    assert line.message == "Order o1"
    assert isinstance(line.var, OrderCompletedEvent)
    assert line.var.level is not None and line.var.level.mask == level
    assert line.var.channels is not None and line.var.channels.mask == Channel.business
    assert line.var.domain is ShopDomain
    assert line.var.domain_name == "shop"


async def test_the_authors_instance_stays_as_it_was_built() -> None:
    event = _event()

    await _box(_RecordingLogger()).info(Channel.business, "text", event)

    assert event.level is None
    assert event.model_dump()["order_id"] == "o1"
    assert "level" not in event.model_dump()


@pytest.mark.parametrize(
    "template",
    [
        "Order {%var.order_id}",
        "{%var.total|red} x",
        "{%var.total|debug}",
        "{%var.item.name}",
        "{%var.level.name}/{%var.channels.names}/{%var.domain_name}",
        "{iif({%var.total} > 5; 'big'; 'small')}",
        "{%var.card}",
        "{%state.paid}",
        "{%scope.action}",
    ],
)
async def test_a_template_renders_the_same_with_kwargs_and_with_an_event(template: str) -> None:
    logger = _RecordingLogger()
    box = _box(logger)
    event = _event()

    await box.info(Channel.business, template, order_id="o1", total=9.5, item=event.item, card=event.card)
    await box.info(Channel.business, template, event)

    assert logger.lines[0].message == logger.lines[1].message


@pytest.mark.parametrize("template", ["{%var.absent}", "{%var._private}"])
async def test_a_broken_template_fails_the_same_with_an_event(template: str) -> None:
    with pytest.raises(LogTemplateError):
        await _box(_RecordingLogger()).info(Channel.business, template, _event())


async def test_a_sensitive_property_of_an_event_is_masked() -> None:
    logger = _RecordingLogger()

    await _box(logger).info(Channel.business, "{%var.card_shown}", _event())

    assert "4111222233334444" not in logger.lines[0].message
    assert logger.lines[0].message.startswith("41")


@pytest.mark.parametrize(
    ("subscription", "delivered"),
    [
        ({"channels": Channel.business}, True),
        ({"channels": Channel.debug}, False),
        ({"levels": Level.info}, True),
        ({"levels": Level.critical}, False),
        ({"domains": ShopDomain}, True),
    ],
)
async def test_a_subscription_filters_an_event_like_any_line(subscription: dict[str, Any], delivered: bool) -> None:
    logger = _RecordingLogger()
    logger.subscribe("rule", **subscription)

    await _box(logger).info(Channel.business, "text", _event())

    assert bool(logger.lines) is delivered


async def test_a_logger_reading_by_key_works_on_both_forms() -> None:
    seen: list[tuple[str, str, bool]] = []

    class ByKeyLogger(BaseLogger):
        """A logger written for lines with ``kwargs``."""

        async def write(
            self,
            scope: LogScope,
            message: str,
            var: dict[str, Any],
            ctx: Context,
            state: BaseState,
            params: BaseParams,
            indent: int,
        ) -> None:
            """Read the line by key."""
            seen.append((var["level"].name, var["channels"].names, var.get("domain") is ShopDomain))

    box = _box(ByKeyLogger())
    await box.info(Channel.business, "text", order_id="o1")
    await box.info(Channel.business, "text", _event())

    assert seen[0] == seen[1]


async def test_an_event_with_kwargs_is_refused() -> None:
    logger = _RecordingLogger()
    with pytest.raises(EventContractError, match="extra"):
        await _box(logger).info(Channel.business, "text", _event(), extra=1)
    assert not logger.lines


@pytest.mark.parametrize("value", [OrderCompletedEvent, {"order_id": "o1"}, BaseEvent()])
async def test_anything_else_in_the_events_place_is_refused(value: Any) -> None:
    logger = _RecordingLogger()
    with pytest.raises(EventContractError):
        await _box(logger).info(Channel.business, "text", value)
    assert not logger.lines


async def test_a_keyword_named_event_stays_a_variable() -> None:
    logger = _RecordingLogger()

    await _box(logger).info(Channel.business, "{%var.event}", event="login")

    assert logger.lines[0].message == "login"


async def test_a_template_with_no_variables_is_delivered_with_an_event() -> None:
    logger = _RecordingLogger()

    await _box(logger).info(Channel.business, "text", _event())

    assert logger.lines[0].message == "text"
    assert isinstance(logger.lines[0].var, OrderCompletedEvent)


@pytest.mark.parametrize(("tool", "level"), TOOLS)
async def test_a_line_with_kwargs_keeps_its_dictionary(tool: str, level: Level) -> None:
    logger = _RecordingLogger()

    await getattr(_box(logger), tool)(Channel.business, "Order {%var.order_id}", order_id="o1")

    line = logger.lines[0]
    assert line.message == "Order o1"
    assert type(line.var) is dict
    assert line.var["order_id"] == "o1"
    assert line.var["level"].mask == level
    assert line.var["channels"].mask == Channel.business
    assert line.var["domain"] is ShopDomain
    assert line.var["domain_name"] == "shop"


@pytest.mark.parametrize(("tool", "level"), TOOLS)
async def test_a_line_with_no_variables_is_delivered_with_no_switch_on(tool: str, level: Level) -> None:
    logger = _RecordingLogger()

    await getattr(_box(logger), tool)(Channel.business, "text")

    line = logger.lines[0]
    assert line.message == "text"
    assert type(line.var) is dict
    assert set(line.var) == {"level", "channels", "domain", "domain_name"}
    assert line.var["level"].mask == level


@pytest.mark.parametrize(
    ("key", "error"),
    [("level", ValueError), ("domain", ValueError), ("domain_name", ValueError), ("channels", TypeError)],
)
async def test_a_reserved_key_in_kwargs_is_still_refused(key: str, error: type[Exception]) -> None:
    logger = _RecordingLogger()
    with pytest.raises(error):
        await _box(logger).info(Channel.business, "text", **{key: 1})
    assert not logger.lines
