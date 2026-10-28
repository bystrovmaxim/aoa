# packages/maxitor/src/maxitor/viewer/model/core/resources/source_checks.py
"""
SourceChecks — the clock and the background runner of the freshness checks.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The checks that keep held graphs current are actions (spec 028, FR-071 … FR-075). Something
has to run them when no request does: every ten seconds ``CheckDueSourcesAction``, which picks
the sources that are due, and on request one ``CheckSourceAction`` in the background — for a
read that answered from memory and found its source's check old (FR-073). This resource is
that something. It decides nothing: which sources are due, and what a check does, are the
actions' rules; it only runs them on the machine with the connections it was given.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    lifespan ──start(every)──► loop ──every 10 s──► machine.run(CheckDueSourcesAction)
    GraphFingerprintAction ──run_soon(source)──► task ──► machine.run(CheckSourceAction)
    lifespan ──close()──► loop and tasks cancelled
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Mapping
from typing import Any

from maxitor.viewer.model.core.core_domain import CoreDomain

from aoa.action_machine.context import Context
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.resources.base_controller import BaseController
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine

#: Connection key under which actions receive the runner.
SOURCE_CHECKS_CONNECTION_KEY = "SourceChecks"

#: How often the clock asks which sources are due.
CHECK_EVERY_SECONDS = 10.0


@meta(description="Runs the freshness checks of held graphs on a clock and in the background", domain=CoreDomain)
class SourceChecks(BaseController):
    """
    AI-CORE-BEGIN
    ROLE: Run the check actions when no request does: on a clock, and once in the background on request.
    CONTRACT: ``bind`` gives the machine and, per action, the connections it runs with; ``start`` starts
    the clock; ``run_soon`` schedules one action run; ``close`` cancels everything not finished.
    INVARIANTS: Decides nothing; a failing run never stops the clock.
    AI-CORE-END
    """

    def __init__(self) -> None:
        self._machine: ActionProductMachine | None = None
        self._connections: dict[type[BaseAction[Any, Any]], dict[str, BaseResource]] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._clock: asyncio.Task[None] | None = None

    def get_wrapper_class(self) -> type[BaseController] | None:
        """Return ``None``: nested actions use this same runner."""
        return None

    async def check_rollup_support(self) -> bool:
        """Report that the runner is not a rollup target."""
        return False

    def bind(self, machine: ActionProductMachine, connections: Mapping[type[BaseAction[Any, Any]], dict[str, BaseResource]]) -> None:
        """Give the machine the runs go on, and the connections each action is run with."""
        self._machine = machine
        self._connections = dict(connections)

    def start(self, action_class: type[BaseAction[Any, Any]], params: BaseParams, every: float = CHECK_EVERY_SECONDS) -> None:
        """Run ``action_class`` with ``params`` every ``every`` seconds until ``close``."""

        async def tick() -> None:
            while True:
                await asyncio.sleep(every)
                await self._run(action_class, params)

        self._clock = asyncio.create_task(tick())

    def run_soon(self, action_class: type[BaseAction[Any, Any]], params: BaseParams) -> None:
        """Run ``action_class`` with ``params`` once, in the background."""
        task = asyncio.create_task(self._run(action_class, params))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def close(self) -> None:
        """Stop the clock and cancel the runs not finished."""
        for task in [*self._tasks, *([self._clock] if self._clock else [])]:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()
        self._clock = None

    async def _run(self, action_class: type[BaseAction[Any, Any]], params: BaseParams) -> None:
        """One run on the machine; its failure is the action's to log, never the clock's to die of."""
        machine = self._machine
        if machine is None:
            raise RuntimeError("SourceChecks.bind(machine, connections) was not called")
        # The action logs what it did; an error that escapes it must not end the clock.
        with contextlib.suppress(Exception):
            await machine.run(Context(), action_class(), params, self._connections.get(action_class, {}))
