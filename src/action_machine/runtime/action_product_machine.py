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
``ConnectionValidator``, ``AspectExecutor``, ``ErrorHandlerExecutor``,
``SagaCoordinator``); this class wires order and
``PluginCoordinator`` for all machine-owned plugin lifecycle emissions
(global start/finish and regular/summary aspect events).

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    run(context, action, params, connections)
        │
        └── _run_internal(nested_level=0, rollup=False)
                │
                ├── action_node = get_action_node_by_id(action_cls)
                ├── _role_checker.check(context, action_node)
                ├── conns = _connection_validator.validate(action, connections, action_node)
                ├── plugin_ctx = await _plugin_coordinator.create_run_context()
                ├── log = ScopedLogger(..., domain=action_node.domain.target_node.node_obj)
                ├── box = ToolsBox(..., factory=DependencyFactory(action_node.resolved_dependency_infos()))
                ├── _plugin_coordinator.emit_global_start(...)
                ├── _execute_pipeline_aspects(...)
                │       ├── per regular aspect:
                │       │       _plugin_coordinator.emit_before_regular_aspect(...)
                │       │       _aspect_executor.execute_regular(...)
                │       │       _plugin_coordinator.emit_after_regular_aspect(...)
                │       ├── _plugin_coordinator.emit_before_summary_aspect(...)
                │       ├── _aspect_executor.execute_summary(...)
                │       ├── _plugin_coordinator.emit_after_summary_aspect(...)
                │       └── on exception (saga_stack prefilled):
                │               _saga_coordinator.execute(saga_stack=..., ...)   [if stack]
                │               _error_handler_executor.handle(...)
                ├── _plugin_coordinator.emit_global_finish(...)
                └── return Result

``ScopedLogger`` and ``DependencyFactory`` are constructed in ``_run_internal``
(``factory`` from ``resolved_dependency_infos()`` on the wired ``action_node``).

**Where plugin events are emitted**

- This module does **not** call ``plugin_ctx.emit_event`` or construct the six
  machine-owned event types directly. It delegates to ``PluginCoordinator``:
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

**Graph access**

Protocol adapters and tools should use ``graph_coordinator`` (``NodeGraphCoordinator``
from ``create_node_graph_coordinator``, built during machine initialization unless
injected).

"""

from __future__ import annotations

import time
from functools import partial
from typing import Any, TypeVar, cast

from action_machine.context.context import Context
from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from action_machine.logging.channel import Channel
from action_machine.logging.domain_resolver import resolve_domain
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.plugin.plugin import Plugin
from action_machine.plugin.plugin_coordinator import PluginCoordinator
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
from action_machine.system_core.type_introspection import TypeIntrospection
from graph.create_node_graph_coordinator import create_node_graph_coordinator
from graph.node_graph_coordinator import NodeGraphCoordinator

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class ActionProductMachine(BaseActionMachine):
    """
    AI-CORE-BEGIN
    ROLE: Public production machine entry point.
    CONTRACT: ``run`` → orchestrated pipeline; keyword-only component overrides.
    INVARIANTS: ``NodeGraphCoordinator`` is built eagerly from ``create_node_graph_coordinator()`` unless injected; interchange ``ActionGraphNode`` resolves role composition and downstream gates for each action class.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        plugins: list[Plugin] | None = None,
        plugin_coordinator: PluginCoordinator | None = None,
        log_coordinator: LogCoordinator | None = None,
        graph_coordinator: NodeGraphCoordinator | None = None,
        role_checker: RoleChecker | None = None,
        connection_validator: ConnectionValidator | None = None,
        aspect_executor: AspectExecutor | None = None,
        error_handler_executor: ErrorHandlerExecutor | None = None,
        saga_coordinator: SagaCoordinator | None = None,
    ) -> None:
        """Keyword-only injectable overrides; build the default graph coordinator eagerly."""
        plugins = plugins or []
        self._log_coordinator = log_coordinator or LogCoordinator()
        self._plugin_coordinator = plugin_coordinator or PluginCoordinator(
            plugins,
            self._log_coordinator,
        )
        self.graph_coordinator = graph_coordinator or create_node_graph_coordinator()
        self._role_checker = role_checker or RoleChecker()
        self._connection_validator = connection_validator or ConnectionValidator()
        self._aspect_executor = aspect_executor or AspectExecutor(self._log_coordinator)
        self._error_handler_executor = error_handler_executor or ErrorHandlerExecutor(
            self._plugin_coordinator
        )
        self._saga_coordinator = saga_coordinator or SagaCoordinator(
            self._aspect_executor,
            self._error_handler_executor,
            self._plugin_coordinator,
        )

    def get_action_node_by_id(self, action_cls: type) -> ActionGraphNode[BaseAction[Any, Any]]:
        """Return the materialized ``Action`` graph node for ``action_cls`` (same id as :class:`ActionGraphNode`)."""
        if not isinstance(action_cls, type) or not issubclass(action_cls, BaseAction):
            raise TypeError(
                f"action_cls must be a subclass of BaseAction, got {action_cls!r}."
            )
        return cast(
            ActionGraphNode[BaseAction[Any, Any]],
            self.graph_coordinator.get_node_by_id(
                TypeIntrospection.full_qualname(action_cls),
                ActionGraphNode.NODE_TYPE,
            ),
        )

    # Aspect pipeline + error path
    # ─────────────────────────────────────────────────────────────────────

    async def _log_rollback_failure(
        self,
        *,
        rollback_error: Exception,
        action: BaseAction[P, R],
        nested_level: int,
        context: Context,
    ) -> None:
        """Best-effort critical log when saga rollback infrastructure fails."""
        try:
            log = ScopedLogger(
                coordinator=self._log_coordinator,
                nest_level=nested_level,
                action_name=action.get_full_class_name(),
                aspect_name="",
                context=context,
                state=BaseState(),
                params=None,
                domain=resolve_domain(type(action)),
            )
            await log.critical(
                Channel.error,
                "Saga rollback failed while handling pipeline error: {%var.rollback_error}",
                rollback_error=str(rollback_error),
            )
        except Exception:
            pass

    async def _execute_pipeline_aspects(
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
            state = BaseState()
            for aspect_node in action_graph_node.get_regular_aspect_graph_nodes():
                failed_aspect_name = aspect_node.label
                state_passed_into_aspect = state

                compensator_node = action_graph_node.compensator_graph_node_for_aspect(
                    aspect_node.label
                )
                if compensator_node is not None:
                    saga_stack.append(
                        SagaFrame(
                            compensator=compensator_node,
                            aspect_name=aspect_node.label,
                            state_before=state_passed_into_aspect,
                            state_after=None,
                        )
                    )

                await self._plugin_coordinator.emit_before_regular_aspect(
                    plugin_ctx,
                    action=action,
                    context=context,
                    params=params,
                    nest_level=box.nested_level,
                    aspect_name=aspect_node.label,
                    state_snapshot=state_passed_into_aspect.to_dict(),
                )

                state, new_state_dict, aspect_duration = (
                    await self._aspect_executor.execute_regular(
                        action=action,
                        aspect_node=aspect_node,
                        params=params,
                        state=state_passed_into_aspect,
                        box=box,
                        connections=connections,
                        context=context,
                    )
                )

                if compensator_node is not None and saga_stack:
                    saga_stack[-1] = SagaFrame(
                        compensator=compensator_node,
                        aspect_name=aspect_node.label,
                        state_before=state_passed_into_aspect,
                        state_after=state,
                    )

                await self._plugin_coordinator.emit_after_regular_aspect(
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

            failed_aspect_name = "summary aspect is not defined in action"
            summary_node = action_graph_node.get_summary_aspect_graph_node()
            failed_aspect_name = summary_node.label

            await self._plugin_coordinator.emit_before_summary_aspect(
                plugin_ctx,
                action=action,
                context=context,
                params=params,
                nest_level=box.nested_level,
                aspect_name=summary_node.label,
                state_snapshot=state.to_dict(),
            )

            result, summary_duration = await self._aspect_executor.execute_summary(
                summary_node=summary_node,
                action=action,
                params=params,
                state=state,
                box=box,
                connections=connections,
                context=context,
            )

            await self._plugin_coordinator.emit_after_summary_aspect(
                plugin_ctx,
                action=action,
                context=context,
                params=params,
                nest_level=box.nested_level,
                aspect_name=summary_node.label,
                state_snapshot=state.to_dict(),
                result=result,
                duration_ms=summary_duration * 1000,
            )
            return cast("R", result)

        except Exception as aspect_error:
            try:
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
            except Exception as rollback_error:
                await self._log_rollback_failure(
                    rollback_error=rollback_error,
                    action=action,
                    nested_level=box.nested_level,
                    context=context,
                )

            error_handler_nodes = action_graph_node.get_error_handler_graph_nodes()
            handled_result = await self._error_handler_executor.handle(
                error=aspect_error,
                action=action,
                params=params,
                state=state if state is not None else BaseState(),
                box=box,
                connections=connections,
                error_handler_nodes=error_handler_nodes,
                context=context,
                plugin_ctx=plugin_ctx,
                failed_aspect_name=failed_aspect_name,
            )
            return cast("R", handled_result)

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

        guard = getattr(self.graph_coordinator, "assert_no_dag_cycle_violations", None)
        if guard is not None:
            guard()

        action_cls = action.__class__
        action_node = self.get_action_node_by_id(action_cls)
        self._role_checker.check(context, action_node)
        conns = self._connection_validator.validate(action, connections, action_node)
        plugin_ctx = await self._plugin_coordinator.create_run_context()

        log = ScopedLogger(
            coordinator=self._log_coordinator,
            nest_level=current_nest,
            action_name=action_node.node_id,
            aspect_name="",
            context=context,
            state=BaseState(),
            params=params,
            domain=action_node.domain.target_node.node_obj,
        )

        box = ToolsBox(
            run_child=partial(
                self._run_internal,
                context=context,
                resources=resources,
                nested_level=current_nest,
                rollup=rollup,
            ),
            resources=resources,
            log=log,
            nested_level=current_nest,
            rollup=rollup,
            factory=DependencyFactory(action_node.resolved_dependency_infos()),
        )

        await self._plugin_coordinator.emit_global_start(
            plugin_ctx,
            action=action,
            context=context,
            params=params,
            nest_level=current_nest,
        )

        result = await self._execute_pipeline_aspects(
            action, params, box, conns, context, plugin_ctx, action_node
        )

        total_duration = time.time() - start_time

        await self._plugin_coordinator.emit_global_finish(
            plugin_ctx,
            action=action,
            context=context,
            params=params,
            nest_level=current_nest,
            result=cast("BaseResult", result),
            duration_ms=total_duration * 1000,
        )

        return result
