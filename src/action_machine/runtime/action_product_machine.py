# src/action_machine/runtime/action_product_machine.py
"""
Async production implementation of the action execution engine.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``ActionProductMachine`` orchestrates a single action run: role and connection
gates, ``ToolsBox`` construction, the aspect pipeline (regular → summary),
typed plugin lifecycle events, saga rollback on failure, and ``@on_error``
handling. Heavy logic lives in injectable components (``RoleChecker``,
``ConnectionValidator``, ``ToolsBoxFactory``, ``AspectExecutor``,
``ErrorHandlerExecutor``, ``SagaCoordinator``); this class wires order and
shared helpers (execution cache, ``PluginEmitSupport`` for all machine-owned
plugin lifecycle emissions: global start/finish and regular/summary aspect events).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    run(context, action, params, connections)
        │
        └── _run_internal(nested_level=0, rollup=False)
                │
                ├── runtime = _get_execution_cache(action_cls)
                ├── _role_checker.check(action, context, runtime)
                ├── conns = _connection_validator.validate(action, connections, runtime.action_node)
                ├── plugin_ctx = await _plugin_coordinator.create_run_context()
                ├── box = _tools_box_factory.create(factory_resolver=self, ...,
                │         mode, machine_class_name, nest_level, context, ...)
                ├── plugin_emit.emit_global_start(...)
                ├── _execute_aspects_with_error_handling(...)
                │       ├── _execute_regular_aspects (per aspect):
                │       │       plugin_emit.emit_before_regular_aspect(...)
                │       │       _aspect_executor.execute_regular(...)
                │       │       plugin_emit.emit_after_regular_aspect(...)
                │       ├── plugin_emit.emit_before_summary_aspect(...)
                │       ├── _aspect_executor.execute_summary(...)
                │       ├── plugin_emit.emit_after_summary_aspect(...)
                │       └── on exception (saga_stack prefilled):
                │               _saga_coordinator.execute(saga_stack=..., ...)   [if stack]
                │               _error_handler_executor.handle(...)
                ├── plugin_emit.emit_global_finish(...)
                └── return Result

``DependencyFactory`` for ``ToolsBox`` is resolved via the public
``dependency_factory_for`` hook passed as ``DependencyFactoryResolver`` into
``ToolsBoxFactory.create``.

**Where plugin events are emitted**

- This module does **not** call ``plugin_ctx.emit_event`` or construct the six
  machine-owned event types directly. It delegates to ``PluginEmitSupport``:
  ``emit_global_start``, ``emit_global_finish``, ``emit_before_regular_aspect``,
  ``emit_after_regular_aspect``, ``emit_before_summary_aspect``,
  ``emit_after_summary_aspect``.
- ``SagaCoordinator``: ``SagaRollbackStartedEvent``, compensation before/after/failed,
  ``SagaRollbackCompletedEvent``.
- ``ErrorHandlerExecutor``: ``BeforeOnErrorAspectEvent``, ``AfterOnErrorAspectEvent``,
  or ``UnhandledErrorEvent``.

**Context access**

Aspects, compensators, and ``@on_error`` handlers cannot read ``Context`` from
``ToolsBox`` (it is not stored there). ``@context_requires`` is satisfied via
``ContextView`` inside ``AspectExecutor``, ``SagaCoordinator``, and
``ErrorHandlerExecutor``.

**Coordinator access**

Protocol adapters and tools should use the public ``gate_coordinator`` property
instead of private ``_coordinator``.

"""

from __future__ import annotations

import time
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, TypeVar, cast

from action_machine.context.context import Context
from action_machine.exceptions import (
    ActionResultDeclarationError,
    ActionResultTypeError,
    MissingSummaryAspectError,
)
from action_machine.legacy.core import Core
from action_machine.logging.console_logger import ConsoleLogger
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.model.graph_model.action_graph_node import ActionGraphNode
from action_machine.plugin.plugin import Plugin
from action_machine.plugin.plugin_coordinator import PluginCoordinator
from action_machine.plugin.plugin_emit_support import PluginEmitSupport
from action_machine.plugin.plugin_run_context import PluginRunContext
from action_machine.resources.base_resource import BaseResource
from action_machine.runtime.aspect_executor import AspectExecutor
from action_machine.runtime.base_action_machine import BaseActionMachine
from action_machine.runtime.connection_validator import ConnectionValidator
from action_machine.runtime.dependency_factory import DependencyFactory
from action_machine.runtime.error_handler_executor import ErrorHandlerExecutor
from action_machine.runtime.role_checker import RoleChecker
from action_machine.runtime.saga_coordinator import SagaCoordinator
from action_machine.runtime.saga_frame import SagaFrame
from action_machine.runtime.tools_box import ToolsBox
from action_machine.runtime.tools_box_factory import ToolsBoxFactory
from action_machine.system_core import TypeIntrospection
from graph.graph_coordinator import GraphCoordinator

if TYPE_CHECKING:
    from action_machine.legacy.aspect_intent_inspector import AspectIntentInspector
    from action_machine.legacy.checker_intent_inspector import CheckerIntentInspector
    from action_machine.legacy.compensate_intent_inspector import (
        CompensateIntentInspector,
    )
    from action_machine.legacy.on_error_intent_inspector import OnErrorIntentInspector

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class _AspectPipelineError(Exception):
    """
    Internal: attaches the ``BaseState`` relevant at the failing pipeline step.

    The original error is ``__cause__``. ``pipeline_state`` is the state passed
    into the aspect call for ``emit_before`` / ``execute_regular`` failures, or the
    merged state after a successful ``execute_regular`` when ``emit_after`` fails.
    """

    def __init__(self, pipeline_state: BaseState) -> None:
        super().__init__()
        self.pipeline_state = pipeline_state


def _aspect_pipeline_chained_exception(apf: _AspectPipelineError) -> Exception:
    """``Exception`` for saga / ``@on_error`` (``__cause__`` is typed as ``BaseException``)."""
    cause = apf.__cause__
    if isinstance(cause, Exception):
        return cause
    return apf


def _role_spec_from_coordinator(action_cls: type, coordinator: GraphCoordinator) -> Any:
    """Return ``@check_roles`` spec from coordinator facet ``role`` (graph-aligned)."""
    snap = coordinator.get_snapshot(action_cls, "role")
    return getattr(snap, "spec", None) if snap is not None else None


@dataclass(frozen=True)
class _ActionExecutionCache:
    """
    Frozen bundle of facet-derived pipeline metadata for one ``run`` / ``_run_internal``.

    Populated from ``get_snapshot`` for facet rows; ``action_node`` is supplied by the
    caller (typically :class:`ActionGraphNode`). Inspector ``Snapshot`` row types apply
    where relevant (see module INVARIANTS).
    """

    role_spec: Any
    regular_aspects: tuple[AspectIntentInspector.Snapshot.Aspect, ...]
    checkers_by_aspect: dict[str, tuple[CheckerIntentInspector.Snapshot.Checker, ...]]
    has_compensators: bool
    error_handlers: tuple[OnErrorIntentInspector.Snapshot.ErrorHandler, ...]
    summary_aspect: AspectIntentInspector.Snapshot.Aspect | None
    compensators_by_aspect: dict[
        str,
        CompensateIntentInspector.Snapshot.Compensator | None,
    ]
    action_node: ActionGraphNode[BaseAction[Any, Any]]

    @classmethod
    def from_coordinator_facets(
        cls,
        action_cls: type,
        *,
        gate_coordinator: GraphCoordinator,
        action_node: ActionGraphNode[BaseAction[Any, Any]],
    ) -> _ActionExecutionCache:
        """Build cache from facet snapshots (``get_snapshot``); ``action_node`` is passed in."""
        asp_snap = gate_coordinator.get_snapshot(action_cls, "aspect")
        aspects = getattr(asp_snap, "aspects", ()) if asp_snap is not None else ()
        regular = tuple(a for a in aspects if a.aspect_type == "regular")
        summary = next((a for a in aspects if a.aspect_type == "summary"), None)

        ch_snap = gate_coordinator.get_snapshot(action_cls, "checker")
        all_checkers = getattr(ch_snap, "checkers", ()) if ch_snap is not None else ()
        checkers_by_aspect: dict[str, tuple[CheckerIntentInspector.Snapshot.Checker, ...]] = {}
        for a in regular:
            checkers_by_aspect[a.method_name] = tuple(
                c for c in all_checkers if c.method_name == a.method_name
            )

        comp_snap = gate_coordinator.get_snapshot(action_cls, "compensator")
        compensators = getattr(comp_snap, "compensators", ()) if comp_snap is not None else ()
        compensators_by_aspect: dict[
            str,
            CompensateIntentInspector.Snapshot.Compensator | None,
        ] = {}
        for aspect in regular:
            compensators_by_aspect[aspect.method_name] = next(
                (c for c in compensators if c.target_aspect_name == aspect.method_name),
                None,
            )

        eh_snap = gate_coordinator.get_snapshot(action_cls, "error_handler")
        error_handlers = getattr(eh_snap, "error_handlers", ()) if eh_snap is not None else ()

        return cls(
            role_spec=_role_spec_from_coordinator(action_cls, gate_coordinator),
            regular_aspects=regular,
            checkers_by_aspect=checkers_by_aspect,
            has_compensators=len(compensators) > 0,
            error_handlers=error_handlers,
            summary_aspect=summary,
            compensators_by_aspect=compensators_by_aspect,
            action_node=action_node,
        )


class ActionProductMachine(BaseActionMachine):
    """
AI-CORE-BEGIN
    ROLE: Public production machine entry point.
    CONTRACT: ``run`` → orchestrated pipeline; keyword-only component overrides.
    INVARIANTS: built ``GraphCoordinator``; per-run execution cache from facet
      snapshots plus ``ActionGraphNode`` for the action class.
    AI-CORE-END
"""

    @staticmethod
    def create_default_coordinator() -> GraphCoordinator:
        """Create and build coordinator with full default inspector set."""
        return Core.create_coordinator()

    def __init__(
        self,
        mode: str,
        *,
        plugins: list[Plugin] | None = None,
        log_coordinator: LogCoordinator | None = None,
        coordinator: GraphCoordinator | None = None,
        role_checker: RoleChecker | None = None,
        connection_validator: ConnectionValidator | None = None,
        tools_box_factory: ToolsBoxFactory | None = None,
        aspect_executor: AspectExecutor | None = None,
        error_handler_executor: ErrorHandlerExecutor | None = None,
        saga_coordinator: SagaCoordinator | None = None,
    ) -> None:
        """Build machine with optional keyword-only component overrides (all after ``*``).

        Defaults wire ``RoleChecker`` → ``ConnectionValidator`` → ``ToolsBoxFactory`` →
        ``AspectExecutor`` → ``ErrorHandlerExecutor`` → ``SagaCoordinator`` in that order.
        Custom ``saga_coordinator`` must accept ``PluginEmitSupport`` (and other
        deps) if replaced; default wiring passes ``self._plugin_emit``.
        Custom ``AspectExecutor`` must be constructed with ``log_coordinator``,
        ``machine_class_name``, and ``mode``. Custom ``ToolsBoxFactory`` only
        receives ``LogCoordinator``; ``create`` supplies resolver and strings explicitly.

        Raises:
            ValueError: empty ``mode``.
            RuntimeError: ``coordinator`` passed but not built.
        """
        if not mode:
            raise ValueError("mode must be non-empty")

        self._mode: str = mode
        self._plugin_coordinator: PluginCoordinator = PluginCoordinator(
            plugins=plugins or [],
        )

        if log_coordinator is None:
            log_coordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)])
        self._log_coordinator: LogCoordinator = log_coordinator
        self._coordinator = (
            coordinator if coordinator is not None else self.create_default_coordinator()
        )
        if not self._coordinator.is_built:
            raise RuntimeError(
                "ActionProductMachine requires a built GraphCoordinator. "
                "Call register(...).build() before passing custom coordinator.",
            )

        self._plugin_emit = PluginEmitSupport(
            self._log_coordinator,
            machine_class_name=self.__class__.__name__,
            mode=self._mode,
        )

        # Step 1 wiring: extension points and deterministic component order.
        self._role_checker = (
            role_checker if role_checker is not None else RoleChecker(self._coordinator)
        )
        self._connection_validator = (
            connection_validator
            if connection_validator is not None
            else ConnectionValidator()
        )
        self._tools_box_factory = (
            tools_box_factory
            if tools_box_factory is not None
            else ToolsBoxFactory(self._log_coordinator)
        )
        self._aspect_executor = (
            aspect_executor
            if aspect_executor is not None
            else AspectExecutor(
                self._log_coordinator,
                machine_class_name=self.__class__.__name__,
                mode=self._mode,
            )
        )
        self._error_handler_executor = (
            error_handler_executor
            if error_handler_executor is not None
            else ErrorHandlerExecutor(self._plugin_emit)
        )
        self._saga_coordinator = (
            saga_coordinator
            if saga_coordinator is not None
            else SagaCoordinator(
                self._aspect_executor,
                self._error_handler_executor,
                self._plugin_coordinator,
                self._plugin_emit,
            )
        )

    @property
    def gate_coordinator(self) -> GraphCoordinator:
        """Public read-only access to the built ``GraphCoordinator`` (graph, facets).

        Adapters and tools should use this property instead of ``_coordinator``.
        """
        return self._coordinator

    @property
    def plugin_emit_support(self) -> PluginEmitSupport:
        """Public read-only access to plugin event field helpers (base fields + emit extras)."""
        return self._plugin_emit

    def get_node_by_id(self, action_cls: type) -> ActionGraphNode[BaseAction[Any, Any]]:
        """Return the materialized ``Action`` graph node for ``action_cls`` (same id as :class:`ActionGraphNode`)."""
        node_id = TypeIntrospection.full_qualname(action_cls)
        return cast(
            ActionGraphNode[BaseAction[Any, Any]],
            self._coordinator.get_node_by_id(node_id, ActionGraphNode.NODE_TYPE),
        )

    def _get_execution_cache(self, action_cls: type) -> _ActionExecutionCache:
        """Frozen facet snapshots + ``ActionGraphNode`` for one ``_run_internal`` of ``action_cls``."""
        return _ActionExecutionCache.from_coordinator_facets(
            action_cls,
            gate_coordinator=self._coordinator,
            action_node=self.get_node_by_id(action_cls),
        )

    def _dependency_factory_for(self, action_cls: type) -> DependencyFactory:
        snap = self._coordinator.get_snapshot(action_cls, "depends")
        if snap is None or not hasattr(snap, "dependencies"):
            return DependencyFactory(())
        return DependencyFactory(tuple(snap.dependencies))

    def dependency_factory_for(self, action_cls: type) -> DependencyFactory:
        """Public resolver for ``ToolsBoxFactory`` (``DependencyFactoryResolver``)."""
        return self._dependency_factory_for(action_cls)

    # ─────────────────────────────────────────────────────────────────────
    # Regular aspects
    # ─────────────────────────────────────────────────────────────────────

    async def _execute_regular_aspects(
        self,
        action: BaseAction[P, R],
        params: P,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        context: Context,
        plugin_ctx: PluginRunContext,
        saga_stack: list[SagaFrame],
        action_graph_node: ActionGraphNode[BaseAction[Any, Any]],
    ) -> BaseState:
        """Plugins and ``AspectExecutor.execute_regular`` per regular aspect."""
        state = BaseState()

        for aspect_node in action_graph_node.get_regular_aspect_graph_nodes():
            state_passed_into_aspect = state
            compensator_node = action_graph_node.compensator_graph_node_for_aspect(aspect_node.label)
            try:
                await self._plugin_emit.emit_before_regular_aspect(
                    plugin_ctx,
                    action=action,
                    context=context,
                    params=params,
                    nest_level=box.nested_level,
                    aspect_name=aspect_node.label,
                    state_snapshot=state_passed_into_aspect.to_dict(),
                )
            except Exception as exc:
                raise _AspectPipelineError(state_passed_into_aspect) from exc

            try:
                state, new_state_dict, aspect_duration = (
                    await self._aspect_executor.execute_regular(
                        action=action,
                        aspect_node=aspect_node,
                        compensator_node=compensator_node,
                        params=params,
                        state=state_passed_into_aspect,
                        box=box,
                        connections=connections,
                        context=context,
                        saga_stack=saga_stack,
                    )
                )
            except Exception as exc:
                raise _AspectPipelineError(state_passed_into_aspect) from exc

            try:
                await self._plugin_emit.emit_after_regular_aspect(
                    plugin_ctx,
                    action=action,
                    context=context,
                    params=params,
                    nest_level=box.nested_level,
                    aspect_name=aspect_node.label,
                    state_snapshot=state.to_dict(),
                    aspect_result=new_state_dict,
                    duration_ms=aspect_duration * 1000,
                )
            except Exception as exc:
                raise _AspectPipelineError(state) from exc

        return state

    # ─────────────────────────────────────────────────────────────────────
    # Aspect pipeline + error path
    # ─────────────────────────────────────────────────────────────────────

    async def _finish_aspect_pipeline_error(
        self,
        *,
        aspect_error: Exception,
        error_state: BaseState,
        failed_aspect_name: str | None,
        saga_stack: list[SagaFrame],
        action: BaseAction[P, R],
        params: P,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        context: Context,
        action_graph_node: ActionGraphNode[BaseAction[Any, Any]],
        plugin_ctx: PluginRunContext,
    ) -> R:
        """Saga unwind (if any), then ``@on_error`` / unhandled with ``error_state``."""
        if saga_stack:
            await self._saga_coordinator.execute(
                saga_stack=saga_stack,
                error=aspect_error,
                action=action,
                params=params,
                box=box,
                connections=connections,
                context=context,
                plugin_ctx=plugin_ctx,
            )
        error_handler_nodes = action_graph_node.get_error_handler_graph_nodes()
        handled_result = await self._error_handler_executor.handle(
            error=aspect_error,
            action=action,
            params=params,
            state=error_state,
            box=box,
            connections=connections,
            error_handler_nodes=error_handler_nodes,
            context=context,
            plugin_ctx=plugin_ctx,
            failed_aspect_name=failed_aspect_name,
        )
        return cast("R", handled_result)

    async def _rollback_saga_if_any(
        self,
        saga_stack: list[SagaFrame],
        error: Exception,
        *,
        action: BaseAction[P, R],
        params: P,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        context: Context,
        plugin_ctx: PluginRunContext,
    ) -> None:
        """Unwind saga frames when aborting after successful regular aspects (e.g. summary contract)."""
        if not saga_stack:
            return
        await self._saga_coordinator.execute(
            saga_stack=saga_stack,
            error=error,
            action=action,
            params=params,
            box=box,
            connections=connections,
            context=context,
            plugin_ctx=plugin_ctx,
        )

    async def _execute_aspects_with_error_handling(
        self,
        action: BaseAction[P, R],
        params: P,
        box: ToolsBox,
        connections: dict[str, BaseResource],
        context: Context,
        plugin_ctx: PluginRunContext,
        action_graph_node: ActionGraphNode[BaseAction[Any, Any]],
    ) -> R:
        """Run regular and summary aspects; on failure, unwind saga then handle error."""
        saga_stack: list[SagaFrame] = []
        failed_aspect_name: str | None = None
        state: BaseState | None = None

        try:
            state = await self._execute_regular_aspects(
                action, params, box, connections, context, plugin_ctx, saga_stack, action_graph_node,
            )

            summary_node = action_graph_node.get_summary_aspect_graph_node()
            summary_name = summary_node.label if summary_node is not None else "summary"
            failed_aspect_name = summary_name
            state_passed_into_summary = state

            try:
                await self._plugin_emit.emit_before_summary_aspect(
                    plugin_ctx,
                    action=action,
                    context=context,
                    params=params,
                    nest_level=box.nested_level,
                    aspect_name=summary_name,
                    state_snapshot=state_passed_into_summary.to_dict(),
                )
            except Exception as exc:
                raise _AspectPipelineError(state_passed_into_summary) from exc

            try:
                result, summary_duration = await self._aspect_executor.execute_summary(
                    summary_node=summary_node,
                    action=action,
                    params=params,
                    state=state_passed_into_summary,
                    box=box,
                    connections=connections,
                    context=context,
                )
            except (
                ActionResultTypeError,
                MissingSummaryAspectError,
                ActionResultDeclarationError,
            ):
                raise
            except Exception as exc:
                raise _AspectPipelineError(state_passed_into_summary) from exc

            try:
                await self._plugin_emit.emit_after_summary_aspect(
                    plugin_ctx,
                    action=action,
                    context=context,
                    params=params,
                    nest_level=box.nested_level,
                    aspect_name=summary_name,
                    state_snapshot=state_passed_into_summary.to_dict(),
                    result=result,
                    duration_ms=summary_duration * 1000,
                )
            except Exception as exc:
                raise _AspectPipelineError(state_passed_into_summary) from exc

            return cast("R", result)

        except _AspectPipelineError as apf:
            return await self._finish_aspect_pipeline_error(
                aspect_error=_aspect_pipeline_chained_exception(apf),
                error_state=apf.pipeline_state,
                failed_aspect_name=failed_aspect_name,
                saga_stack=saga_stack,
                action=action,
                params=params,
                box=box,
                connections=connections,
                context=context,
                action_graph_node=action_graph_node,
                plugin_ctx=plugin_ctx,
            )
        except (
            ActionResultTypeError,
            MissingSummaryAspectError,
            ActionResultDeclarationError,
        ) as contract_exc:
            # Regular aspects may have run with side effects; unwind saga before surfacing
            # a developer contract violation (wrong Result / missing summary). Do not run
            # @on_error — the failure is not business logic in an aspect.
            await self._rollback_saga_if_any(
                saga_stack,
                contract_exc,
                action=action,
                params=params,
                box=box,
                connections=connections,
                context=context,
                plugin_ctx=plugin_ctx,
            )
            raise
        except Exception as aspect_error:
            return await self._finish_aspect_pipeline_error(
                aspect_error=aspect_error,
                error_state=state if state is not None else BaseState(),
                failed_aspect_name=failed_aspect_name,
                saga_stack=saga_stack,
                action=action,
                params=params,
                box=box,
                connections=connections,
                context=context,
                action_graph_node=action_graph_node,
                plugin_ctx=plugin_ctx,
            )

    # ─────────────────────────────────────────────────────────────────────
    # Public entry: run
    # ─────────────────────────────────────────────────────────────────────

    async def run(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        connections: dict[str, BaseResource] | None = None,
    ) -> R:
        """Execute one action; production uses ``rollup=False`` and ``nested_level=0``."""
        # pylint: disable=invalid-overridden-method
        return await self._run_internal(
            context=context,
            action=action,
            params=params,
            resources=None,
            connections=connections,
            nested_level=0,
            rollup=False,
        )

    async def _run_internal(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type, Any] | None,
        connections: dict[str, BaseResource] | None,
        nested_level: int,
        rollup: bool,
    ) -> R:
        """Single run level with fresh plugin context and local saga stack."""
        current_nest = nested_level + 1
        start_time = time.time()

        action_cls = action.__class__
        runtime = self._get_execution_cache(action_cls)
        action_node = runtime.action_node
        self._role_checker.check(action, context, runtime)
        conns = self._connection_validator.validate(action, connections, action_node)
        plugin_ctx = await self._plugin_coordinator.create_run_context()
        run_child = partial(
            self._run_child,
            context=context,
            resources=resources,
            nested_level=current_nest,
            rollup=rollup,
        )

        box = self._tools_box_factory.create(
            factory_resolver=self,
            nest_level=current_nest,
            context=context,
            action_cls=action.__class__,
            params=params,
            resources=resources,
            rollup=rollup,
            run_child=run_child,
            mode=self._mode,
            machine_class_name=self.__class__.__name__,
        )

        await self._plugin_emit.emit_global_start(
            plugin_ctx,
            action=action,
            context=context,
            params=params,
            nest_level=current_nest,
        )

        result = await self._execute_aspects_with_error_handling(
            action, params, box, conns, context, plugin_ctx, action_node
        )

        total_duration = time.time() - start_time

        await self._plugin_emit.emit_global_finish(
            plugin_ctx,
            action=action,
            context=context,
            params=params,
            nest_level=current_nest,
            result=cast("BaseResult", result),
            duration_ms=total_duration * 1000,
        )

        return result

    async def _run_child(
        self,
        action: BaseAction[Any, Any],
        params: BaseParams,
        connections: dict[str, BaseResource] | None = None,
        *,
        context: Context,
        resources: dict[type, Any] | None,
        nested_level: int,
        rollup: bool,
    ) -> BaseResult:
        """Run a child action within the current execution scope."""
        return await self._run_internal(
            context=context,
            action=action,
            params=params,
            resources=resources,
            connections=connections,
            nested_level=nested_level,
            rollup=rollup,
        )
