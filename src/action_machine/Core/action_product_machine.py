# src/action_machine/core/action_product_machine.py
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
shared helpers (execution cache, plugin event base fields).

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Pipeline metadata for scratch mode is read from the action **class** scratch
  attributes (aspects, checkers, compensators, error handlers, connection keys).
  Role spec for execution comes from ``GateCoordinator.get_snapshot(cls, "role")``
  (same source as the graph).
- ``CoordinatorActionProductMachine`` overrides only cache and dependency-factory
  construction; orchestration sequence stays identical.
- Each ``_run_internal`` call owns a **local** saga stack; nested ``run_child``
  calls get independent stacks.
- When ``rollup=True``, successful regular aspects do not append saga frames;
  compensators are not driven by this stack (transactional rollback uses
  connection wrappers in production paths).
- Compensator failures during rollback never replace the original aspect error;
  they are reported via ``CompensateFailedEvent`` (see ``SagaCoordinator``).

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
                ├── conns = _connection_validator.validate(action, connections, runtime)
                ├── plugin_ctx = await _plugin_coordinator.create_run_context()
                ├── box = _tools_box_factory.create(self, nest_level, context,
                │         action_cls, params, resources, rollup, run_child)
                ├── emit GlobalStartEvent
                ├── _execute_aspects_with_error_handling(...)
                │       ├── _execute_regular_aspects (per aspect):
                │       │       emit BeforeRegularAspectEvent
                │       │       _aspect_executor.execute_regular(...)
                │       │       emit AfterRegularAspectEvent
                │       ├── emit BeforeSummaryAspectEvent
                │       ├── _aspect_executor.execute_summary(...)
                │       ├── emit AfterSummaryAspectEvent
                │       └── on exception (saga_stack prefilled):
                │               _saga_coordinator.execute(...)   [if stack non-empty]
                │               _error_handler_executor.handle(...)
                ├── emit GlobalFinishEvent
                └── return Result

``DependencyFactory`` for ``ToolsBox`` is resolved inside ``ToolsBoxFactory``,
not as a separate step on the machine.

**Where plugin events are emitted**

- This module: ``GlobalStartEvent``, ``GlobalFinishEvent``, ``BeforeRegularAspectEvent``,
  ``AfterRegularAspectEvent``, ``BeforeSummaryAspectEvent``, ``AfterSummaryAspectEvent``.
- ``SagaCoordinator``: ``SagaRollbackStartedEvent``, compensation before/after/failed,
  ``SagaRollbackCompletedEvent``.
- ``ErrorHandlerExecutor``: ``BeforeOnErrorAspectEvent``, ``AfterOnErrorAspectEvent``,
  or ``UnhandledErrorEvent``.

**Context access**

Aspects, compensators, and ``@on_error`` handlers do not read ``Context`` directly
from ``ToolsBox``; ``@context_requires`` is satisfied via ``ContextView`` inside
``AspectExecutor``, ``SagaCoordinator``, and ``ErrorHandlerExecutor``.

═══════════════════════════════════════════════════════════════════════════════
COMPATIBILITY GUARANTEES
═══════════════════════════════════════════════════════════════════════════════

- Constructor extension points are keyword-only parameters after ``*``:
  ``role_checker``, ``connection_validator``, ``tools_box_factory``,
  ``aspect_executor``, ``error_handler_executor``, ``saga_coordinator``.
- Default behavior remains unchanged when extension points are not provided.
- Compatibility contract is behavioral (pipeline order + event semantics),
  not private-method availability.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Happy path: ``await machine.run(ctx, action, params, connections)`` completes
after all regular aspects, summary, and ``GlobalFinishEvent``.

Edge case: an aspect raises after earlier aspects ran — ``SagaCoordinator``
unwinds frames in reverse order, then ``ErrorHandlerExecutor`` runs a matching
``@on_error`` handler or re-raises after ``UnhandledErrorEvent``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Empty ``mode`` raises ``ValueError``. An unbuilt custom ``coordinator`` raises
  ``RuntimeError``.
- Role, connection, checker, and handler failures preserve existing exception types
  (e.g. ``AuthorizationError``, ``ConnectionValidationError``, ``ValidationFieldError``,
  ``OnErrorHandlerError``) from delegated components.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Thin orchestrator over decomposed core components.
CONTRACT: run/_run_internal sequence; scratch cache + facet role spec;
  component DI via keyword-only constructor args.
INVARIANTS: local saga stack per run; rollback before @on_error; typed plugin
  emission split between machine, SagaCoordinator, ErrorHandlerExecutor.
FLOW: cache → gates → tools box → aspect pipeline → finish event.
FAILURES: component and pipeline exceptions unchanged by orchestration layer.
EXTENSION POINTS: role_checker, connection_validator, tools_box_factory,
  aspect_executor, error_handler_executor, saga_coordinator.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, TypeVar, cast

from action_machine.aspects.aspect_gate_host_inspector import AspectGateHostInspector
from action_machine.checkers.checker_gate_host_inspector import CheckerGateHostInspector
from action_machine.compensate.compensate_gate_host_inspector import (
    CompensateGateHostInspector,
)
from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_action_machine import BaseActionMachine
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.components.aspect_executor import AspectExecutor
from action_machine.core.components.connection_validator import ConnectionValidator
from action_machine.core.components.error_handler_executor import ErrorHandlerExecutor
from action_machine.core.components.role_checker import RoleChecker
from action_machine.core.components.saga_coordinator import SagaCoordinator
from action_machine.core.components.tools_box_factory import ToolsBoxFactory
from action_machine.core.core_action_machine import CoreActionMachine
from action_machine.core.saga_frame import SagaFrame
from action_machine.core.tools_box import ToolsBox
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.logging.console_logger import ConsoleLogger
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.metadata.gate_coordinator import GateCoordinator
from action_machine.on_error.on_error_gate_host_inspector import OnErrorGateHostInspector
from action_machine.plugins.events import (
    AfterRegularAspectEvent,
    AfterSummaryAspectEvent,
    BeforeRegularAspectEvent,
    BeforeSummaryAspectEvent,
    GlobalFinishEvent,
    GlobalStartEvent,
)
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_coordinator import PluginCoordinator
from action_machine.plugins.plugin_run_context import PluginRunContext
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


def _scratch_aspects(
    cls: type[BaseAction],
) -> list[AspectGateHostInspector.Snapshot.Aspect]:
    return list(cls.scratch_aspects())


def _scratch_checkers_for_aspect(
    cls: type[BaseAction],
    aspect_name: str,
    func: Any,
) -> tuple[CheckerGateHostInspector.Snapshot.Checker, ...]:
    return tuple(cls.scratch_checkers_for_aspect(aspect_name, method_ref=func))


def _scratch_error_handlers(
    cls: type[BaseAction],
) -> tuple[OnErrorGateHostInspector.Snapshot.ErrorHandler, ...]:
    return tuple(cls.scratch_error_handlers())


def _scratch_compensators(
    cls: type[BaseAction],
) -> tuple[CompensateGateHostInspector.Snapshot.Compensator, ...]:
    return tuple(cls.scratch_compensators())


def _scratch_connection_keys(cls: type[BaseAction]) -> tuple[str, ...]:
    return tuple(cls.scratch_connection_keys())


def _role_spec_from_coordinator(action_cls: type, coordinator: GateCoordinator) -> Any:
    """Return ``@check_roles`` spec from coordinator facet ``role`` (graph-aligned)."""
    snap = coordinator.get_snapshot(action_cls, "role")
    return getattr(snap, "spec", None) if snap is not None else None


@dataclass(frozen=True)
class _ActionExecutionCache:
    """Per-run snapshot from class scratch attributes (roles, connections, pipeline)."""

    role_spec: Any
    connection_keys: tuple[str, ...]
    regular_aspects: tuple[AspectGateHostInspector.Snapshot.Aspect, ...]
    checkers_by_aspect: dict[str, tuple[CheckerGateHostInspector.Snapshot.Checker, ...]]
    has_compensators: bool
    error_handlers: tuple[OnErrorGateHostInspector.Snapshot.ErrorHandler, ...]
    summary_aspect: AspectGateHostInspector.Snapshot.Aspect | None
    compensators_by_aspect: dict[
        str,
        CompensateGateHostInspector.Snapshot.Compensator | None,
    ]

    @classmethod
    def from_action_class(
        cls,
        action_cls: type,
        *,
        gate_coordinator: GateCoordinator,
    ) -> _ActionExecutionCache:
        aspects = _scratch_aspects(action_cls)
        regular = tuple(a for a in aspects if a.aspect_type == "regular")
        summary = next((a for a in aspects if a.aspect_type == "summary"), None)
        checkers_by_aspect = {
            a.method_name: _scratch_checkers_for_aspect(action_cls, a.method_name, a.method_ref)
            for a in regular
        }
        compensators = _scratch_compensators(action_cls)
        compensators_by_aspect: dict[
            str,
            CompensateGateHostInspector.Snapshot.Compensator | None,
        ] = {}
        for aspect in regular:
            compensators_by_aspect[aspect.method_name] = next(
                (c for c in compensators if c.target_aspect_name == aspect.method_name),
                None,
            )
        return cls(
            role_spec=_role_spec_from_coordinator(action_cls, gate_coordinator),
            connection_keys=_scratch_connection_keys(action_cls),
            regular_aspects=regular,
            checkers_by_aspect=checkers_by_aspect,
            has_compensators=len(compensators) > 0,
            error_handlers=_scratch_error_handlers(action_cls),
            summary_aspect=summary,
            compensators_by_aspect=compensators_by_aspect,
        )

    @classmethod
    def from_coordinator_facets(
        cls,
        action_cls: type,
        *,
        gate_coordinator: GateCoordinator,
    ) -> _ActionExecutionCache:
        """
        Same pipeline layout as ``from_action_class``, but aspects/checkers/
        compensators/error-handlers/connections come from facet snapshots
        (``get_snapshot``) instead of ``BaseAction.scratch_*`` helpers.
        """
        asp_snap = gate_coordinator.get_snapshot(action_cls, "aspect")
        aspects = getattr(asp_snap, "aspects", ()) if asp_snap is not None else ()
        regular = tuple(a for a in aspects if a.aspect_type == "regular")
        summary = next((a for a in aspects if a.aspect_type == "summary"), None)

        ch_snap = gate_coordinator.get_snapshot(action_cls, "checker")
        all_checkers = getattr(ch_snap, "checkers", ()) if ch_snap is not None else ()
        checkers_by_aspect: dict[str, tuple[CheckerGateHostInspector.Snapshot.Checker, ...]] = {}
        for a in regular:
            checkers_by_aspect[a.method_name] = tuple(
                c for c in all_checkers if c.method_name == a.method_name
            )

        comp_snap = gate_coordinator.get_snapshot(action_cls, "compensator")
        compensators = getattr(comp_snap, "compensators", ()) if comp_snap is not None else ()
        compensators_by_aspect: dict[
            str,
            CompensateGateHostInspector.Snapshot.Compensator | None,
        ] = {}
        for aspect in regular:
            compensators_by_aspect[aspect.method_name] = next(
                (c for c in compensators if c.target_aspect_name == aspect.method_name),
                None,
            )

        eh_snap = gate_coordinator.get_snapshot(action_cls, "error_handler")
        error_handlers = getattr(eh_snap, "error_handlers", ()) if eh_snap is not None else ()

        conn_snap = gate_coordinator.get_snapshot(action_cls, "connections")
        if conn_snap is not None:
            connection_keys = tuple(c.key for c in conn_snap.connections)
        else:
            connection_keys = ()

        return cls(
            role_spec=_role_spec_from_coordinator(action_cls, gate_coordinator),
            connection_keys=connection_keys,
            regular_aspects=regular,
            checkers_by_aspect=checkers_by_aspect,
            has_compensators=len(compensators) > 0,
            error_handlers=error_handlers,
            summary_aspect=summary,
            compensators_by_aspect=compensators_by_aspect,
        )


class ActionProductMachine(BaseActionMachine):
    """Async action runner; delegates stages to core components (see module docstring).

    AI-CORE-BEGIN
    ROLE: Public production machine entry point.
    CONTRACT: ``run`` → orchestrated pipeline; keyword-only component overrides.
    INVARIANTS: built ``GateCoordinator``; per-run execution cache from scratch
      (role facet from coordinator).
    AI-CORE-END
    """

    @staticmethod
    def create_default_coordinator() -> GateCoordinator:
        """Create and build coordinator with full default inspector set."""
        return CoreActionMachine.create_coordinator()

    def __init__(
        self,
        mode: str,
        *,
        plugins: list[Plugin] | None = None,
        log_coordinator: LogCoordinator | None = None,
        coordinator: GateCoordinator | None = None,
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
        Custom ``saga_coordinator`` must satisfy its own dependencies if replaced.

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
                "ActionProductMachine requires a built GateCoordinator. "
                "Call register(...).build() before passing custom coordinator.",
            )

        # Step 1 wiring: extension points and deterministic component order.
        self._role_checker = (
            role_checker if role_checker is not None else RoleChecker(self._coordinator)
        )
        self._connection_validator = (
            connection_validator
            if connection_validator is not None
            else ConnectionValidator(self._coordinator)
        )
        self._tools_box_factory = (
            tools_box_factory
            if tools_box_factory is not None
            else ToolsBoxFactory(self._log_coordinator, self._coordinator)
        )
        self._aspect_executor = (
            aspect_executor if aspect_executor is not None else AspectExecutor()
        )
        self._error_handler_executor = (
            error_handler_executor
            if error_handler_executor is not None
            else ErrorHandlerExecutor()
        )
        self._saga_coordinator = (
            saga_coordinator
            if saga_coordinator is not None
            else SagaCoordinator(
                self._aspect_executor,
                self._error_handler_executor,
                self._plugin_coordinator,
                self._log_coordinator,
            )
        )

    def _get_execution_cache(self, action_cls: type) -> _ActionExecutionCache:
        return _ActionExecutionCache.from_action_class(
            action_cls,
            gate_coordinator=self._coordinator,
        )

    def _dependency_factory_for(self, action_cls: type) -> DependencyFactory:
        return DependencyFactory(tuple(getattr(action_cls, "_depends_info", ()) or ()))

    # ─────────────────────────────────────────────────────────────────────
    # Общие поля для создания событий
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _base_event_fields(
        action: BaseAction[Any, Any],
        context: Context,
        params: BaseParams,
        nest_level: int,
    ) -> dict[str, Any]:
        """Shared kwargs for ``BasePluginEvent`` subclasses emitted from this machine."""
        return {
            "action_class": type(action),
            "action_name": action.get_full_class_name(),
            "nest_level": nest_level,
            "context": context,
            "params": params,
        }

    # ─────────────────────────────────────────────────────────────────────
    # Формирование kwargs для emit_event
    # ─────────────────────────────────────────────────────────────────────

    def _build_plugin_emit_kwargs(self, nest_level: int) -> dict[str, Any]:
        """Extra kwargs passed to ``plugin_ctx.emit_event`` (log + machine identity)."""
        return {
            "log_coordinator": self._log_coordinator,
            "machine_name": self.__class__.__name__,
            "mode": self._mode,
        }

    # ─────────────────────────────────────────────────────────────────────
    # Выполнение regular-аспектов
    # ─────────────────────────────────────────────────────────────────────

    async def _execute_regular_aspects(
        self,
        action: BaseAction[P, R],
        params: P,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Context,
        runtime: _ActionExecutionCache,
        plugin_ctx: PluginRunContext,
        saga_stack: list[SagaFrame],
    ) -> BaseState:
        """Run regular aspects: plugin events + ``AspectExecutor.execute_regular``.

        Mutates ``saga_stack`` in place when ``runtime.has_compensators`` and not rollup
        (empty list passed otherwise). Aspect exceptions propagate to
        ``_execute_aspects_with_error_handling``.
        """
        state = BaseState()
        regular_aspects = runtime.regular_aspects
        base_fields = self._base_event_fields(action, context, params, box.nested_level)
        plugin_kwargs = self._build_plugin_emit_kwargs(box.nested_level)

        # Стек компенсации — локальный для этого конвейера.
        # Не создаётся при rollup=True.
        build_saga = runtime.has_compensators

        for aspect_meta in regular_aspects:
            # ── BeforeRegularAspectEvent ──────────────────────────────
            await plugin_ctx.emit_event(
                BeforeRegularAspectEvent(
                    **base_fields,
                    aspect_name=aspect_meta.method_name,
                    state_snapshot=state.to_dict(),
                ),
                **plugin_kwargs,
            )

            state, new_state_dict, aspect_duration = (
                await self._aspect_executor.execute_regular(
                    self,
                    aspect_meta=aspect_meta,
                    action=action,
                    params=params,
                    state=state,
                    box=box,
                    connections=connections,
                    context=context,
                    runtime=runtime,
                    saga_stack=saga_stack if build_saga else [],
                )
            )

            # ── AfterRegularAspectEvent ───────────────────────────────
            await plugin_ctx.emit_event(
                AfterRegularAspectEvent(
                    **base_fields,
                    aspect_name=aspect_meta.method_name,
                    state_snapshot=state.to_dict(),
                    aspect_result=new_state_dict,
                    duration_ms=aspect_duration * 1000,
                ),
                **plugin_kwargs,
            )

        return state

    # ─────────────────────────────────────────────────────────────────────
    # Выполнение конвейера с обработкой ошибок
    # ─────────────────────────────────────────────────────────────────────

    async def _execute_aspects_with_error_handling(
        self,
        action: BaseAction[P, R],
        params: P,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        context: Context,
        runtime: _ActionExecutionCache,
        plugin_ctx: PluginRunContext,
    ) -> R:
        """Aspect pipeline: regular + summary; on error, saga then ``@on_error``.

        ``saga_stack`` is created before ``try`` so ``except`` sees frames from aspects
        that completed before the failure.
        """
        base_fields = self._base_event_fields(action, context, params, box.nested_level)
        plugin_kwargs = self._build_plugin_emit_kwargs(box.nested_level)

        saga_stack: list[SagaFrame] = []
        failed_aspect_name: str | None = None

        try:
            state = await self._execute_regular_aspects(
                action, params, box, connections, context, runtime, plugin_ctx,
                saga_stack,
            )

            summary_meta = runtime.summary_aspect
            summary_name = summary_meta.method_name if summary_meta else "summary"

            # ── BeforeSummaryAspectEvent ──────────────────────────────
            await plugin_ctx.emit_event(
                BeforeSummaryAspectEvent(
                    **base_fields,
                    aspect_name=summary_name,
                    state_snapshot=state.to_dict(),
                ),
                **plugin_kwargs,
            )

            failed_aspect_name = summary_name
            result, summary_duration = await self._aspect_executor.execute_summary(
                self,
                summary_meta=summary_meta,
                action=action,
                params=params,
                state=state,
                box=box,
                connections=connections,
                context=context,
            )

            # ── AfterSummaryAspectEvent ───────────────────────────────
            await plugin_ctx.emit_event(
                AfterSummaryAspectEvent(
                    **base_fields,
                    aspect_name=summary_name,
                    state_snapshot=state.to_dict(),
                    result=cast("BaseResult", result),
                    duration_ms=summary_duration * 1000,
                ),
                **plugin_kwargs,
            )

            return cast("R", result)

        except Exception as aspect_error:
            # ── Размотка стека компенсации (Saga) ─────────────────────
            # Выполняется ДО @on_error: сначала откат побочных эффектов,
            # потом обработка бизнес-логики. Иначе @on_error работает
            # с неконсистентными данными.
            if saga_stack:
                await self._saga_coordinator.execute(
                    self,
                    saga_stack=saga_stack,
                    error=aspect_error,
                    action=action,
                    params=params,
                    box=box,
                    connections=connections,
                    context=context,
                    plugin_ctx=plugin_ctx,
                )

            # ── Делегируем обработку ошибки ────────────────────────────
            error_state = BaseState()
            handled_result = await self._error_handler_executor.handle(
                self,
                error=aspect_error,
                action=action,
                params=params,
                state=error_state,
                box=box,
                connections=connections,
                runtime=runtime,
                context=context,
                plugin_ctx=plugin_ctx,
                failed_aspect_name=failed_aspect_name,
            )
            return cast("R", handled_result)

    # ─────────────────────────────────────────────────────────────────────
    # Публичный API: run (асинхронный)
    # ─────────────────────────────────────────────────────────────────────

    async def run(
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        connections: dict[str, BaseResourceManager] | None = None,
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
        connections: dict[str, BaseResourceManager] | None,
        nested_level: int,
        rollup: bool,
    ) -> R:
        """Single run level: gates, ``ToolsBox``, global plugin events, aspect pipeline."""
        current_nest = nested_level + 1
        start_time = time.time()
        plugin_kwargs = self._build_plugin_emit_kwargs(current_nest)

        action_cls = action.__class__
        runtime = self._get_execution_cache(action_cls)
        self._role_checker.check(action, context, runtime)
        conns = self._connection_validator.validate(action, connections, runtime)
        plugin_ctx = await self._plugin_coordinator.create_run_context()

        async def run_child(
            action: BaseAction[Any, Any],
            params: BaseParams,
            connections: dict[str, BaseResourceManager] | None = None,
        ) -> BaseResult:
            return await self._run_internal(
                context=context,
                action=action,
                params=params,
                resources=resources,
                connections=connections,
                nested_level=current_nest,
                rollup=rollup,
            )

        box = self._tools_box_factory.create(
            self,
            nest_level=current_nest,
            context=context,
            action_cls=action.__class__,
            params=params,
            resources=resources,
            rollup=rollup,
            run_child=run_child,
        )

        base_fields = self._base_event_fields(action, context, params, current_nest)

        # ── GlobalStartEvent ──────────────────────────────────────
        await plugin_ctx.emit_event(
            GlobalStartEvent(**base_fields),
            **plugin_kwargs,
        )

        result = await self._execute_aspects_with_error_handling(
            action, params, box, conns, context, runtime, plugin_ctx,
        )

        total_duration = time.time() - start_time

        # ── GlobalFinishEvent ─────────────────────────────────────
        await plugin_ctx.emit_event(
            GlobalFinishEvent(
                **base_fields,
                result=cast("BaseResult", result),
                duration_ms=total_duration * 1000,
            ),
            **plugin_kwargs,
        )

        return result
