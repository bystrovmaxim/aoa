# src/action_machine/runtime/machines/sync_action_product_machine.py
"""
Sync production runtime machine for action execution.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``SyncActionProductMachine`` is the synchronous counterpart of
``ActionProductMachine``. Its ``run()`` method is a normal (non-async) method
that creates an event loop via ``asyncio.run()`` and executes the async
pipeline inside it.

Typical use cases:
- CLI scripts.
- Celery tasks without async worker mode.
- Synchronous web handlers (for example, non-async Django views).
- Any code path without an active event loop.

═══════════════════════════════════════════════════════════════════════════════
DIFFERENCE FROM ActionProductMachine
═══════════════════════════════════════════════════════════════════════════════

    ActionProductMachine:
        async def run(...) -> R              <- requires await
        Usage: await machine.run(ctx, action, params)

    SyncActionProductMachine:
        def run(...) -> R                    <- regular call
        Usage: result = machine.run(ctx, action, params)

Internal implementation (``_run_internal``) is inherited from
``ActionProductMachine`` unchanged. ``SyncActionProductMachine`` only overrides
the public entry point ``run()``, wrapping async execution with ``asyncio.run()``.

═══════════════════════════════════════════════════════════════════════════════
ROLLUP
═══════════════════════════════════════════════════════════════════════════════

Production machine always passes ``rollup=False`` into ``_run_internal()``.
Rollup is not part of the public production machine API.

Rollup is available only through TestBench, which calls ``_run_internal()``
directly with rollup-enabled terminal methods.

═══════════════════════════════════════════════════════════════════════════════
LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

Do not call ``run()`` inside an already running event loop. In async contexts
(for example, FastAPI endpoint handlers), ``asyncio.run()`` raises
``RuntimeError``. Use ``ActionProductMachine`` there.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseActionMachine (ABC)
        │
        ├── ActionProductMachine          (async, production)
        │
        └── SyncActionProductMachine      (sync, production)  <- this class

``SyncActionProductMachine`` inherits ``ActionProductMachine`` and reuses the
entire pipeline logic (roles, connections, checkers, plugins, rollup
propagation internals). Only public ``run()`` is overridden.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.runtime.machines.sync_action_product_machine import SyncActionProductMachine

    machine = SyncActionProductMachine(mode="production")

    # Synchronous call - no await:
    result = machine.run(context, action, params)

    # In a CLI script:
    if __name__ == "__main__":
        ctx = Context()
        action = PingAction()
        params = PingAction.Params()
        result = machine.run(ctx, action, params)
        print(result.message)

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``run()`` cannot be used from an active async event loop.
- Public API intentionally fixes ``rollup=False`` for production safety.
- All runtime contract failures propagate from inherited async pipeline.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Synchronous adapter over ActionProductMachine async pipeline.
CONTRACT: run(...) synchronously executes _run_internal via asyncio.run.
INVARIANTS: Inherited orchestration semantics; public rollup is always false.
FLOW: sync run call -> asyncio.run -> inherited async pipeline execution.
FAILURES: RuntimeError in active loop; pipeline errors propagate unchanged.
EXTENSION POINTS: Use async ActionProductMachine for event-loop-native contexts.
AI-CORE-END
"""

import asyncio
from typing import TypeVar

from action_machine.context.context import Context
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.machines.action_product_machine import ActionProductMachine

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class SyncActionProductMachine(ActionProductMachine):
    """
    Synchronous production runtime machine.

    Reuses full async pipeline from ``ActionProductMachine`` and exposes a sync
    ``run()`` entry point via ``asyncio.run()``.
    """

    def run(  # type: ignore[override]  # pylint: disable=invalid-overridden-method
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Execute action synchronously via ``asyncio.run`` wrapper.

        Always delegates to ``_run_internal(..., rollup=False, nested_level=0)``.
        """
        return asyncio.run(
            self._run_internal(
                context=context,
                action=action,
                params=params,
                resources=None,
                connections=connections,
                nested_level=0,
                rollup=False,
            )
        )
