# packages/aoa-action-machine/src/aoa/action_machine/runtime/action_product_machine.py
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
                ├── _role_checker.check(context, action_node, params)
                ├── conns = _connection_validator.validate(action, connections, action_node)
                ├── plugin_ctx = await _plugin_coordinator.create_run_context()
                ├── log = ScopedLogger(..., domain=action_node.domain.target_node.node_obj)
                ├── box = ToolsBox(..., factory=DependencyFactory(action_node.resolved_dependency_infos()))
                ├── _plugin_coordinator.emit_global_start(...)
                ├── optional cache read (``cache_coordinator`` set) or pipeline
                ├── _execute_pipeline_aspects(...)  # skipped on cache hit
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
                ├── optional cache write after clean pipeline
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

Protocol adapters and tools should use ``graph_coordinator`` (:class:`~aoa.action_machine.graph.core.node_graph_coordinator.NodeGraphCoordinator`
built by :func:`~aoa.action_machine.graph.node_graph_coordinator_factory.create_node_graph_coordinator` during machine initialization unless injected).

═══════════════════════════════════════════════════════════════════════════════
CACHE INTEGRATION
═══════════════════════════════════════════════════════════════════════════════

Optional **in-memory** action result cache, enabled only when the machine is
constructed with ``cache_coordinator`` set to a
:class:`~aoa.action_machine.runtime.cache_coordinator.CacheCoordinator` instance
(default ``None`` disables all cache behavior and **does not** invoke action cache
hooks).

**Not in v1:** sharing the coordinator via ``ClassVar`` on ``BaseAction``, or
single-flight / request coalescing for identical keys. Those belong to future design.

**Order inside** ``_run_internal`` (after role and connection gates, ``ToolsBox``,
and ``emit_global_start``): resolve ``cache_key`` and validate it; on a hit,
``read_cache`` may return a result or ``None`` (stale → invalidate and run the
pipeline). On a miss, ``_execute_pipeline_aspects`` runs (regular/summary aspect
plugin events as today). A **cache hit** still emits **global** start and finish,
but **does not** emit regular/summary aspect events because the pipeline is skipped.

After a successful **summary** path (not a result coming only from ``@on_error``),
the machine may call ``on_cache_write`` and, if it returns ``True``, ``put`` on the
coordinator. Handled ``@on_error`` outcomes are never cached. Cache ``duration_ms``
passed to ``on_cache_write`` uses the same ``time.time()``-based wall interval as
``GlobalFinishEvent`` for comparability.

If ``cache_key``, ``read_cache``, ``on_cache_write``, or coordinator I/O raises,
the exception propagates and ``emit_global_finish`` is **not** called in v1.
:exc:`~aoa.action_machine.exceptions.cache_contract_error.CacheContractError` is used
for strict return-value contract violations (invalid key type, empty key string,
non-result from ``read_cache``, non-bool from ``on_cache_write``).

═══════════════════════════════════════════════════════════════════════════════
INCLUDE CONTRACTS (``UseCase.include``, PR-4)
═══════════════════════════════════════════════════════════════════════════════

A :class:`~contextvars.ContextVar` holds the set of action types that entered
``_run_internal`` during the current **root** run. Nested ``await box.run(...)``
shares that set. On a successful root run (after the aspect pipeline, including
results produced only via ``@on_error``), :class:`~aoa.action_machine.runtime.include_contract_checker.IncludeContractChecker`
runs **before** ``emit_global_finish`` unless the root finished with an action-cache
hit (pipeline skipped), in which case the check is skipped because nested runs
from an earlier materialization are not represented in this session.

**Note on** ``asyncio.create_task``: CPython's task context inherits existing
``ContextVar`` values until the task rebinds the variable; awaited
``create_task(box.run(...))`` therefore still contributes types to the same root
tracker. Fire-and-forget tasks that complete **after** the root action has already
passed include verification are not modeled and should be avoided for ``include``.

"""

from __future__ import annotations

import time
from contextvars import ContextVar, Token
from dataclasses import dataclass
from functools import partial
from typing import Any, TypeVar, cast

from aoa.action_machine.context.context import Context
from aoa.action_machine.exceptions.cache_contract_error import CacheContractError
from aoa.action_machine.graph.core.node_graph_coordinator import NodeGraphCoordinator
from aoa.action_machine.graph.node_graph_coordinator_factory import create_node_graph_coordinator
from aoa.action_machine.graph.nodes.action_graph_node import ActionGraphNode
from aoa.action_machine.intents.action_schema.action_schema_intent_resolver import ActionSchemaIntentResolver
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.channel import Channel
from aoa.action_machine.logging.console_logger import ConsoleLogger
from aoa.action_machine.logging.domain_resolver import resolve_domain
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.logging.scoped_logger import ScopedLogger
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.plugin.core.plugin import Plugin
from aoa.action_machine.plugin.core.plugin_coordinator import PluginCoordinator
from aoa.action_machine.plugin.core.plugin_run_context import PluginRunContext
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.aspect_executor import AspectExecutor
from aoa.action_machine.runtime.base_action_machine import BaseActionMachine
from aoa.action_machine.runtime.cache_coordinator import CacheCoordinator
from aoa.action_machine.runtime.cache_tag import CacheTag
from aoa.action_machine.runtime.connection_validator import ConnectionValidator
from aoa.action_machine.runtime.dependency_factory import DependencyFactory
from aoa.action_machine.runtime.error_handler_executor import ErrorHandlerExecutor
from aoa.action_machine.runtime.include_contract_checker import IncludeContractChecker
from aoa.action_machine.runtime.role_checker import RoleChecker
from aoa.action_machine.runtime.saga_coordinator import SagaCoordinator
from aoa.action_machine.runtime.saga_frame import SagaFrame
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.action_machine.system_core.type_introspection import TypeIntrospection

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)

# Sentinel used in ActionProductMachine.__init__ to tell apart two distinct caller intents:
#   ActionProductMachine()                      — cache_coordinator not supplied at all
#                                                 → create a CacheCoordinator() automatically
#   ActionProductMachine(cache_coordinator=None) — caller explicitly opted out of caching
#                                                 → leave _cache_coordinator as None
#
# A plain default of None would collapse both cases into the same value, making it
# impossible to distinguish "user forgot to pass it" from "user deliberately disabled it".
# A unique object() instance is never equal to anything else, so the identity check
# ``cache_coordinator is _CACHE_COORDINATOR_DEFAULT`` is always unambiguous.
_CACHE_COORDINATOR_DEFAULT: object = object()

# Tracks ``type(action)`` for every ``_run_internal`` entry in the current root run
# (``ContextVar.get()`` is ``None`` only for the outermost call that owns the set).
_INCLUDE_EXECUTION_TYPES: ContextVar[set[type] | None] = ContextVar(
    "_INCLUDE_EXECUTION_TYPES",
    default=None,
)


@dataclass(frozen=True)
class _PipelineOutcome[R]:
    """
    Return value of ``_execute_pipeline_aspects`` for cache and finish wiring.

    Attributes:
        result: Object from the summary aspect or a matching ``@on_error`` handler.
        from_error_handler: ``True`` when ``result`` was produced only via the error path.
        all_aspect_states: Plugin-readable snapshots derived from saga frames after each
            regular aspect (live objects preserved when ``to_dict()`` would coerce them).
    """

    result: R
    from_error_handler: bool
    all_aspect_states: tuple[dict[str, Any], ...] = ()


def _plugin_snapshot_value_differs(live: Any, dumped: Any) -> bool:
    """True when ``model_dump`` coerced ``live`` (including nested list items)."""
    if type(live) is not type(dumped):
        return True
    if isinstance(live, list):
        if not isinstance(dumped, list) or len(live) != len(dumped):
            return True
        return any(
            _plugin_snapshot_value_differs(live_item, dumped_item)
            for live_item, dumped_item in zip(live, dumped, strict=True)
        )
    return bool(live != dumped)


def _aspect_state_snapshot_for_plugins(state: BaseState) -> dict[str, Any]:
    """Build plugin snapshot; keep live values pydantic would coerce in ``to_dict()``."""
    snapshot = state.to_dict()
    for key in snapshot:
        live = getattr(state, key, None)
        if live is not None and _plugin_snapshot_value_differs(live, snapshot[key]):
            snapshot[key] = live
    return snapshot


def _all_aspect_states_from_saga_stack(
    saga_stack: list[SagaFrame],
) -> tuple[dict[str, Any], ...]:
    """Return successful regular-aspect states already stored in saga frames."""
    return tuple(
        _aspect_state_snapshot_for_plugins(frame.state_after)
        for frame in saga_stack
        if isinstance(frame.state_after, BaseState)
    )


class ActionProductMachine(BaseActionMachine):
    """
    AI-CORE-BEGIN
    ROLE: Public production machine entry point.
    CONTRACT: ``run`` → orchestrated pipeline; keyword-only component overrides.
    INVARIANTS: ``NodeGraphCoordinator`` is built eagerly from ``node_graph_coordinator_factory.create_node_graph_coordinator()`` unless injected; interchange ``ActionGraphNode`` resolves role composition and downstream gates for each action class.
    AI-CORE-END
    """

    def __init__(
        self,
        *,
        plugins: list[Plugin] | None = None,
        loggers: list[BaseLogger] | None = None,
        plugin_coordinator: PluginCoordinator | None = None,
        log_coordinator: LogCoordinator | None = None,
        graph_coordinator: NodeGraphCoordinator | None = None,
        role_checker: RoleChecker | None = None,
        connection_validator: ConnectionValidator | None = None,
        aspect_executor: AspectExecutor | None = None,
        error_handler_executor: ErrorHandlerExecutor | None = None,
        saga_coordinator: SagaCoordinator | None = None,
        cache_coordinator: CacheCoordinator | None = _CACHE_COORDINATOR_DEFAULT,  # type: ignore[assignment]
    ) -> None:
        """Wire injectable components; an in-memory ``CacheCoordinator`` is created by default.

        Pass ``cache_coordinator=None`` to disable caching explicitly.
        """
        self._log_coordinator = log_coordinator or LogCoordinator()
        default_loggers = [] if log_coordinator else [ConsoleLogger()]
        for logger in loggers if loggers is not None else default_loggers:
            self._log_coordinator.add_logger(logger)
        self._plugin_coordinator = plugin_coordinator or PluginCoordinator(log_coordinator=self._log_coordinator)
        for plugin in plugins or []:
            self._plugin_coordinator.add_plugin(plugin)
        self.graph_coordinator = graph_coordinator or create_node_graph_coordinator()
        self._role_checker = role_checker or RoleChecker()
        self._connection_validator = connection_validator or ConnectionValidator()
        self._aspect_executor = aspect_executor or AspectExecutor(self._log_coordinator)
        self._error_handler_executor = error_handler_executor or ErrorHandlerExecutor(self._plugin_coordinator)
        self._saga_coordinator = saga_coordinator or SagaCoordinator(
            self._aspect_executor,
            self._error_handler_executor,
            self._plugin_coordinator,
        )
        self._cache_coordinator: CacheCoordinator | None = (
            CacheCoordinator() if cache_coordinator is _CACHE_COORDINATOR_DEFAULT else cache_coordinator
        )

    @staticmethod
    def _validate_cache_key(cache_key: str | None, action: BaseAction[Any, Any]) -> None:
        """Ensure ``cache_key`` is ``None`` or a non-empty ``str``, or raise :exc:`CacheContractError`."""
        if cache_key is None:
            return
        if not isinstance(cache_key, str):
            raise CacheContractError(
                f"cache_key in {type(action).__name__!r} must return str | None; " f"got {type(cache_key).__name__!r}.",
            )
        if not cache_key.strip():
            raise CacheContractError(
                f"cache_key in {type(action).__name__!r} must not be empty or whitespace-only.",
            )

    @staticmethod
    def _validate_cache_invalidate(invalidations: object, action: BaseAction[Any, Any]) -> None:
        """Ensure ``on_cache_invalidate`` returned ``list[CacheTag] | None`` or raise :exc:`CacheContractError`."""
        if invalidations is None:
            return
        if not isinstance(invalidations, list):
            raise CacheContractError(
                f"on_cache_invalidate in {type(action).__name__!r} must return "
                f"list[CacheTag] | None; got {type(invalidations).__name__!r}.",
            )
        for item in invalidations:
            if not isinstance(item, CacheTag):
                raise CacheContractError(
                    f"on_cache_invalidate in {type(action).__name__!r}: each item must be "
                    f"CacheTag; got {type(item).__name__!r}.",
                )

    @staticmethod
    def _validate_cached_result(
        cached_result: object,
        result_type: type[BaseResult],
        action: BaseAction[Any, Any],
    ) -> None:
        """Ensure ``cached_result`` is an instance of ``result_type`` or raise :exc:`CacheContractError`."""
        if not isinstance(cached_result, result_type):
            raise CacheContractError(
                f"read_cache in {type(action).__name__!r} returned "
                f"{type(cached_result).__name__!r}, expected "
                f"{result_type.__name__!r} or None.",
            )

    @staticmethod
    def _validate_cache_write_decision(
        write_tags: object,
        action: BaseAction[Any, Any],
    ) -> None:
        """Ensure ``on_cache_write`` returned ``list[CacheTag] | None`` or raise :exc:`CacheContractError`."""
        if write_tags is None:
            return
        if not isinstance(write_tags, list):
            raise CacheContractError(
                f"on_cache_write in {type(action).__name__!r} must return list[CacheTag] | None; "
                f"got {type(write_tags).__name__!r}.",
            )
        for item in write_tags:
            if not isinstance(item, CacheTag):
                raise CacheContractError(
                    f"on_cache_write in {type(action).__name__!r}: each item must be CacheTag; "
                    f"got {type(item).__name__!r}.",
                )

    def get_action_node_by_id(self, action_cls: type) -> ActionGraphNode[BaseAction[Any, Any]]:
        """Return the materialized ``Action`` graph node for ``action_cls`` (same id as :class:`ActionGraphNode`)."""
        if not isinstance(action_cls, type) or not issubclass(action_cls, BaseAction):
            raise TypeError(f"action_cls must be a subclass of BaseAction, got {action_cls!r}.")
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
    ) -> _PipelineOutcome[R]:
        """Run aspects; return outcome with ``from_error_handler`` set on error-handler path."""
        saga_stack: list[SagaFrame] = []
        failed_aspect_name: str | None = None
        state: BaseState | None = None

        try:
            state = BaseState()
            for aspect_node in action_graph_node.get_regular_aspect_graph_nodes():
                failed_aspect_name = aspect_node.label
                state_passed_into_aspect = state

                compensator_node = action_graph_node.compensator_graph_node_for_aspect(aspect_node.node_obj)
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

                state, new_state_dict, aspect_duration = await self._aspect_executor.execute_regular(
                    action=action,
                    aspect_node=aspect_node,
                    params=params,
                    state=state_passed_into_aspect,
                    box=box,
                    connections=connections,
                    context=context,
                )

                if saga_stack:
                    saga_stack[-1] = SagaFrame(
                        compensator=compensator_node,
                        aspect_name=aspect_node.label,
                        state_before=state_passed_into_aspect,
                        state_after=state,
                    )

                opaque_fields = frozenset(
                    n.node_obj.field_name
                    for n in getattr(aspect_node, "get_checker_graph_nodes", lambda: [])()
                    if n.node_obj.opaque
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
                    opaque_fields=opaque_fields,
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
            return _PipelineOutcome(
                cast("R", result),
                from_error_handler=False,
                all_aspect_states=_all_aspect_states_from_saga_stack(saga_stack),
            )

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
            return _PipelineOutcome(
                cast("R", handled_result),
                from_error_handler=True,
                all_aspect_states=_all_aspect_states_from_saga_stack(saga_stack),
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

    async def _run_internal(  # pylint: disable=too-many-branches,too-many-statements
        self,
        context: Context,
        action: BaseAction[P, R],
        params: P,
        resources: dict[type, Any] | None,
        connections: dict[str, BaseResource] | None,
        nested_level: int,
        rollup: bool,
    ) -> R:
        """One nested or top-level run: gates, optional cache, pipeline, plugins, return ``result``."""
        current_nest = nested_level + 1
        start_time = time.time()

        active_include_types = _INCLUDE_EXECUTION_TYPES.get()
        include_tracker_reset_token: Token[set[type] | None] | None = None
        owns_include_tracker = False
        if active_include_types is None:
            active_include_types = set()
            include_tracker_reset_token = _INCLUDE_EXECUTION_TYPES.set(active_include_types)
            owns_include_tracker = True
        active_include_types.add(type(action))

        try:
            guard = getattr(self.graph_coordinator, "assert_no_dag_cycle_violations", None)
            if guard is not None:
                guard()

            action_cls = action.__class__
            result_type = ActionSchemaIntentResolver.resolve_result_type(action_cls)
            action_node = self.get_action_node_by_id(action_cls)
            self._role_checker.check(context, action_node, params)
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

            cache_key_str: str | None = None
            cache_hit = False

            if self._cache_coordinator is not None:
                cache_key_str = action.cache_key(params)
                self._validate_cache_key(cache_key_str, action)
                if cache_key_str is not None:
                    entry = await self._cache_coordinator.get_entry(action_cls, cache_key_str)
                    if entry is not None:
                        cached_result = await action.read_cache(params, entry)
                        if cached_result is not None:
                            self._validate_cached_result(cached_result, result_type, action)
                            result = cached_result
                            cache_hit = True
                        else:
                            await self._cache_coordinator.invalidate(action_cls, cache_key_str)

            if not cache_hit:
                outcome = await self._execute_pipeline_aspects(
                    action, params, box, conns, context, plugin_ctx, action_node
                )
                result = outcome.result
                if self._cache_coordinator is not None and not outcome.from_error_handler:
                    total_duration_ms = (time.time() - start_time) * 1000
                    # ORDER: invalidate first, then write.
                    #
                    # Invalidation must precede the write so that the new entry is never
                    # evicted by its own directives. Consider an action that both evicts
                    # CacheTag(type=Order, key=42) AND writes a fresh entry under that same
                    # tag: if the write came first, the subsequent eviction pass would
                    # immediately remove the entry it just stored, leaving the cache empty
                    # after every run. By inverting the order — evict stale entries, then
                    # write the fresh result — the new entry always survives the current cycle.
                    invalidations = await action.on_cache_invalidate(params, result)
                    self._validate_cache_invalidate(invalidations, action)
                    if invalidations:
                        await self._cache_coordinator.evict_by_tags(frozenset(invalidations))
                    # Write only when cache_key returned a non-None key for this call.
                    if cache_key_str is not None:
                        write_tags = await action.on_cache_write(result, params, total_duration_ms)
                        self._validate_cache_write_decision(write_tags, action)
                        if write_tags is not None:
                            await self._cache_coordinator.put(
                                action_cls,
                                cache_key_str,
                                result,
                                total_duration_ms,
                                tags=write_tags,
                            )

            if owns_include_tracker and not cache_hit:
                IncludeContractChecker.verify(action, frozenset(active_include_types))

            total_duration = time.time() - start_time

            finish_snapshots: tuple[dict[str, Any], ...] = ()
            if not cache_hit:
                finish_snapshots = outcome.all_aspect_states

            await self._plugin_coordinator.emit_global_finish(
                plugin_ctx,
                action=action,
                context=context,
                params=params,
                nest_level=current_nest,
                result=cast("BaseResult", result),
                duration_ms=total_duration * 1000,
                all_aspect_states=finish_snapshots,
            )

            return result
        finally:
            if owns_include_tracker and include_tracker_reset_token is not None:
                _INCLUDE_EXECUTION_TYPES.reset(include_tracker_reset_token)
