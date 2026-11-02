# packages/aoa-action-machine/tests/action_machine/runtime/emission_support.py
"""
Emission support — what the tests of the emission rules share.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The events, the recording logger and the method that writes what a test asks for.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.channel import Channel
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.logging.log_scope import LogScope
from aoa.action_machine.model import BaseParams, BaseResult, BaseState
from aoa.action_machine.model.base_event import BaseEvent
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

KINDS = ("access", "regular", "compensate", "handler", "summary")


class ListedEvent(BaseEvent):
    """The fact every typed method lists."""

    order_id: str


class AlsoListedEvent(BaseEvent):
    """A second listed fact."""


class UnlistedEvent(BaseEvent):
    """A fact no method lists."""


@dataclass(frozen=True)
class _Line:
    """One written line."""

    method: str
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
        self.lines.append(_Line(getattr(scope, "aspect", ""), message, var))

    def messages(self) -> list[str]:
        """Return the text of every line."""
        return [line.message for line in self.lines]


class _Params(BaseParams):
    """Says which method speaks, what it writes, and whether the run fails."""

    speaker: str = Field(default="", description="The kind of method that writes")
    write: str = Field(default="", description="What it writes")
    fail: bool = Field(default=False, description="Whether a later step fails")


class _Result(BaseResult):
    """Says who answered."""

    outcome: str = Field(description="Who produced the result")


async def _say(box: ToolsBox, params: _Params, kind: str) -> None:
    """Write what the params ask for, when this kind is the speaker; a helper shares the method's box."""
    if params.speaker != kind:
        return
    if params.write == "listed":
        await box.info(Channel.business, "listed {%var.order_id}", ListedEvent(order_id="o1"))
    elif params.write == "unlisted":
        await box.info(Channel.business, "unlisted", UnlistedEvent())
    elif params.write == "kwargs":
        await box.info(Channel.business, "kwargs {%var.x}", x=1)
    elif params.write == "plain":
        await box.info(Channel.business, "plain")
    elif params.write == "broken":
        await box.info(Channel.business, "{%var.absent}", UnlistedEvent())


def _machine(logger: BaseLogger, **kwargs: Any) -> ActionProductMachine:
    """Build a machine that writes to ``logger``."""
    return ActionProductMachine(log_coordinator=LogCoordinator(loggers=[logger]), **kwargs)


def _params(speaker: str, write: str) -> _Params:
    """Ask ``speaker`` to write ``write``; the two kinds that run on failure need the failure."""
    return _Params(speaker=speaker, write=write, fail=speaker in ("compensate", "handler"))
