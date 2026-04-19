# src/action_machine/runtime/base_action_machine.py
"""
Abstract base class for all ActionMachine runtime machines.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``BaseActionMachine`` defines the contract shared by all runtime machines.
A machine is the central executor that accepts action instance, input params,
execution context, and resource connections, then runs the action pipeline with
role checks, validations, and plugin notifications.

═══════════════════════════════════════════════════════════════════════════════
MACHINE HIERARCHY
═══════════════════════════════════════════════════════════════════════════════

``BaseActionMachine`` exposes two API layers:

1. PUBLIC: abstract ``run()`` entry point for callers.
   Concrete machines define whether it is async (``ActionProductMachine``)
   or sync (``SyncActionProductMachine``).

2. INTERNAL: ``_run_internal()`` pipeline implementation with support for
   nesting, resources, and rollup flag. Called from ``run()`` and recursively
   from ``ToolsBox.run()`` for child actions.

═══════════════════════════════════════════════════════════════════════════════
ROLLUP PARAMETER
═══════════════════════════════════════════════════════════════════════════════

``rollup: bool`` in ``_run_internal()`` controls transaction rollback mode.
Production machines (``ActionProductMachine``, ``SyncActionProductMachine``)
always pass ``rollup=False``. TestBench-style runners pass rollup explicitly
through terminal methods so tester chooses mode intentionally.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    BaseActionMachine (ABC)
        │
        ├── ActionProductMachine          (async, production)
        │
        └── SyncActionProductMachine      (sync, production)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

1. STATELESS BETWEEN RUNS: machine keeps no mutable cross-request state.
   Every run is isolated.

2. NO SILENT SUPPRESSION: runtime errors are propagated to caller.

3. ``_run_internal`` CONTRACT: all concrete machines implement a consistent
   signature including resources, connections, nested_level, and rollup.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path:
    Public ``run(...)`` delegates to machine-specific pipeline implementation
    and returns typed ``BaseResult`` subclass ``R``.

Edge case:
    A concrete machine that does not implement ``_run_internal`` raises
    ``NotImplementedError`` when execution reaches internal pipeline.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- This class defines contracts only and does not perform execution itself.
- Concrete machine behavior (async/sync orchestration) is implementation-specific.
- Runtime validation/error semantics are delegated to concrete pipelines.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Shared abstract contract for runtime machine entry points.
CONTRACT: Expose public run API and internal _run_internal pipeline hook.
INVARIANTS: Stateless between runs; no silent error suppression.
FLOW: caller invokes run -> concrete machine delegates to _run_internal.
FAILURES: NotImplementedError until concrete runtime machine implements internals.
EXTENSION POINTS: Async/sync implementations override run and _run_internal.
AI-CORE-END
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from action_machine.context.context import Context
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.resources.base_resource_manager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class BaseActionMachine(ABC):
    """
    Abstract base class for all runtime machines.

    Defines public ``run()`` contract and internal ``_run_internal()`` hook.
    Concrete machines provide async/sync entry behavior and full pipeline logic.
    """

    @abstractmethod
    async def run(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Execute action and return typed result.

        Public entry point. Async machines expose coroutine semantics; sync
        machines provide regular call semantics.
        """
        pass

    async def _run_internal(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type[Any], Any] | None,
        connections: dict[str, BaseResourceManager] | None,
        nested_level: int,
        rollup: bool,
    ) -> R:
        """
        Internal pipeline execution hook with nesting and rollup support.

        Called from ``run()`` at root level and recursively for child actions.
        """
        raise NotImplementedError
