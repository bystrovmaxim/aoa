"""
03_custom_plugin.py — Write your own plugin

A plugin is an OBSERVER of the machine's lifecycle, never a participant. It
reacts to typed, frozen events (it cannot mutate them, the result, or the state)
and is perfect for metrics, audit, tracing, side-effect logging.

You implement two things on `Plugin`:

  - `async get_initial_state()` — fresh per-run state (the machine calls it once
    per run; the state is threaded through this plugin's handlers and discarded
    at run end);
  - one or more `@on(EventClass, ...)` handlers with the fixed 4-arg signature
    `async def handler(self, state, event, log) -> state` — each returns the
    (possibly updated) state.

Because per-run state is discarded, anything that must survive across runs goes
into external storage injected in the constructor (here: a plain list `sink`).

Register the plugin once: `ActionProductMachine(plugins=[...])`.

How-to: ../../docs/how-to/authoring-plugin_draft.md

Run:
    uv run python examples/how_to/03_custom_plugin.py
"""

import asyncio
from typing import Any

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.context import Context
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.intents.on import AspectEvent, GlobalFinishEvent, on
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.plugin.core import Plugin
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


# ── The plugin: count aspect events per run, record each finish to a sink ────
class CallAuditPlugin(Plugin):
    def __init__(self, sink: list[tuple[str, int]]) -> None:
        super().__init__()                 # optional watch_actions / watch_events filters
        self._sink = sink                  # external storage survives across runs

    async def get_initial_state(self) -> dict[str, Any]:
        return {"aspect_events": 0}        # fresh state for THIS run

    @on(AspectEvent)                       # matches every before/after aspect event
    async def on_count_aspects(self, state, event: AspectEvent, log) -> dict[str, Any]:
        state["aspect_events"] += 1
        return state                       # threaded into the next handler (method name must start with on_)

    @on(GlobalFinishEvent)                 # one per completed run (+ result, duration_ms)
    async def on_record_finish(self, state, event: GlobalFinishEvent, log) -> dict[str, Any]:
        short = event.action_name.rsplit(".", 1)[-1]
        self._sink.append((short, state["aspect_events"]))
        return state


# ── A normal Action — it knows nothing about the plugin ──────────────────────
class GreetingDomain(BaseDomain):
    name = "greeting"
    description = "Greetings domain"


class GreetParams(BaseParams):
    name: str = Field(description="Person to greet")


class GreetResult(BaseResult):
    message: str = Field(description="Greeting")


@meta(description="Greet a person", domain=GreetingDomain)
@check_roles(GuestRole)
class GreetAction(BaseAction[GreetParams, GreetResult]):
    @summary_aspect("Build greeting")
    async def greet_summary(self, params, state, box, connections):
        return GreetResult(message=f"Hello, {params.name}!")


async def main() -> None:
    sink: list[tuple[str, int]] = []
    machine = ActionProductMachine(plugins=[CallAuditPlugin(sink)])

    for who in ("Alice", "Bob"):
        await machine.run(Context(), GreetAction(), GreetParams(name=who), {})

    print("sink (action, aspect_events) per run ->", sink)


if __name__ == "__main__":
    asyncio.run(main())
