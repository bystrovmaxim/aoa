"""
04_custom_logger.py — Write your own logger

A logger is a SINK for business events emitted from aspects via `box.info /
warning / critical(...)`. To send those events somewhere new (Kafka, Slack,
PagerDuty, a JSON file), subclass `BaseLogger` and implement ONE method:

    async def write(self, scope, message, var, ctx, state, params, indent) -> None

The coordinator does the rest before `write` is called: it validates `var`,
substitutes templates (`{%var.x}`, `{iif(...)}`), and fans out to every logger.
The message string arrives already rendered. Per-message metadata lives in `var`:

    var["level"]    -> LogLevelPayload(mask=Level.*, name="INFO" | "WARNING" | ...)
    var["channels"] -> LogChannelPayload(mask=Channel.*, names="business" | ...)
    var.get("domain")  -> a BaseDomain subclass or None

Filtering is inherited: with no `subscribe(...)` a logger accepts everything;
with subscriptions it accepts a message if ANY rule matches (channels AND levels
AND domains inside one rule). Here the logger ships structured records to an
in-memory `sink` and subscribes to WARNING only — so an INFO line is dropped.

Wire it: `ActionProductMachine(log_coordinator=LogCoordinator(loggers=[...]))`.

How-to: ../../docs/how-to/authoring-logger_draft.md

Run:
    uv run python examples/how_to/04_custom_logger.py
"""

import asyncio
import json
from typing import Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.logging import Channel, Level
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


# ── The logger: ship each accepted line as a structured record to a sink ─────
class JsonLinesLogger(BaseLogger):
    def __init__(self, sink: list[dict[str, Any]]) -> None:
        super().__init__()                 # sets up the subscribe/match/handle pipeline
        self._sink = sink

    async def write(self, scope, message, var, ctx, state, params, indent) -> None:
        self._sink.append({
            "level": var["level"].name,            # "INFO" / "WARNING" / "CRITICAL"
            "channels": var["channels"].names,     # "business", ...
            "message": self.strip_ansi_codes(message),  # already substituted by coordinator
        })


# ── A normal Action that logs business events ────────────────────────────────
class RootDomain(BaseDomain):
    name = "root"
    description = "Root domain"


class PayParams(BaseParams):
    amount: float = Field(description="Amount")


class PayResult(BaseResult):
    ok: bool = Field(description="Accepted")


@meta(description="Take a payment", domain=RootDomain)
@check_roles(GuestRole)
class PayAction(BaseAction[PayParams, PayResult]):
    @summary_aspect("Charge")
    async def charge_summary(self, params, state, box, connections):
        await box.info(Channel.business, "Charging {%var.amount}", amount=params.amount)
        await box.warning(Channel.business, "Large amount {%var.amount} flagged", amount=params.amount)
        return PayResult(ok=True)


async def main() -> None:
    sink: list[dict[str, Any]] = []
    logger = JsonLinesLogger(sink).subscribe("warn-only", levels=Level.warning)  # filter: WARNING only
    machine = ActionProductMachine(log_coordinator=LogCoordinator(loggers=[logger]))

    await machine.run(Context(), PayAction(), PayParams(amount=5000.0), {})

    print("shipped records (INFO dropped by subscription):")
    for rec in sink:
        print("  " + json.dumps(rec, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
