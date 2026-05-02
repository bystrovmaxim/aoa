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
``PluginEmitSupport`` for all machine-owned plugin lifecycle emissions
(global start/finish and regular/summary aspect events).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    run(context, action, params, connections)
        │
        └── _run_internal(nested_level=0, rollup=False)
                │
                ├── action_node = get_node_by_id(action_cls)
                ├── _role_checker.check(context, action_node)
                ├── conns = _connection_validator.validate(action, connections, action_node)
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
from functools import partial
from typing import Any, TypeVar, cast

from action_machine.context.context import Context
from action_machine.exceptions import (
    ActionResultDeclarationError,
    ActionResultTypeError,
    MissingSummaryAspectError,
)
from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from action_machine.legacy.core import Core
from action_machine.logging.console_logger import ConsoleLogger
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
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


class ActionProductMachine(BaseActionMachine):
    """
    AI-CORE-BEGIN
    ROLE: Public production machine entry point.
    CONTRACT: ``run`` → orchestrated pipeline; keyword-only component overrides.
    INVARIANTS: built ``GraphCoordinator``; interchange ``ActionGraphNode`` resolves role composition and downstream gates for each action class.
    AI-CORE-END
    """

    def __init__(
        self,
        mode: str,
        *,
        plugins: list[Plugin] | None = None,
        log_coordinator: LogCoordinator = LogCoordinator(loggers=[ConsoleLogger(use_colors=True)]),
        coordinator: GraphCoordinator = Core.create_coordinator(),
        role_checker: RoleChecker = RoleChecker(),
        connection_validator: ConnectionValidator = ConnectionValidator(),
        tools_box_factory: ToolsBoxFactory | None = None,
        aspect_executor: AspectExecutor | None = None,
        error_handler_executor: ErrorHandlerExecutor | None = None,
        saga_coordinator: SagaCoordinator | None = None,
    ) -> None:
        """Keyword-only injectable overrides (``None`` supplies defaults below).

        Raises:
            ValueError: ``mode`` is empty.
        """
        if not mode:
            raise ValueError("mode must be non-empty")

        self._mode: str = mode
        self._plugin_coordinator: PluginCoordinator = PluginCoordinator(
            list(plugins if plugins is not None else [])
        )
        self._log_coordinator: LogCoordinator = log_coordinator
        self._coordinator: GraphCoordinator = coordinator

        self._plugin_emit = PluginEmitSupport(
            self._log_coordinator,
            machine_class_name=self.__class__.__name__,
            mode=self._mode,
        )

        self._role_checker: RoleChecker = role_checker
        self._connection_validator: ConnectionValidator = connection_validator
        self._tools_box_factory: ToolsBoxFactory = (
            ToolsBoxFactory(self._log_coordinator)
            if tools_box_factory is None
            else tools_box_factory
        )
        self._aspect_executor: AspectExecutor = (
            AspectExecutor(
                self._log_coordinator,
                machine_class_name=self.__class__.__name__,
                mode=self._mode,
            )
            if aspect_executor is None
            else aspect_executor
        )
        self._error_handler_executor: ErrorHandlerExecutor = (
            ErrorHandlerExecutor(self._plugin_emit)
            if error_handler_executor is None
            else error_handler_executor
        )
        self._saga_coordinator: SagaCoordinator = (
            SagaCoordinator(
                self._aspect_executor,
                self._error_handler_executor,
                self._plugin_coordinator,
                self._plugin_emit,
            )
            if saga_coordinator is None
            else saga_coordinator
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

            if action_graph_node.summary_aspect:
                summary_node = action_graph_node.get_summary_aspect_graph_node()
                summary_name = summary_node.label
            else:
                summary_node = None
                summary_name = "summary"
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
        action_node = self.get_node_by_id(action_cls)
        self._role_checker.check(context, action_node)
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
