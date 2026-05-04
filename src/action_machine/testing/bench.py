# src/action_machine/testing/bench.py
"""
TestBench - unified immutable entry point for testing ActionMachine actions.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

TestBench is the central object of testing infrastructure. It creates a
collection of machines (async + sync), executes action on each, and compares
results. If results differ, ``ResultMismatchError`` is raised.

TestBench is immutable: each fluent call (``.with_user``, ``.with_mocks``, etc.)
returns a NEW ``TestBench`` instance with updated field values. Original object
is never mutated, making it safe for parallel usage and predictable in tests.

═══════════════════════════════════════════════════════════════════════════════
LOGGING (SCOPEDLOGGER)
═══════════════════════════════════════════════════════════════════════════════

When TestBench creates ``ScopedLogger`` for ``run_aspect`` / ``run_summary`` /
compensators, it passes ``domain=resolve_domain(action_cls)`` exactly like
production ``ToolsBoxFactory``, so ``var`` payloads and subscriptions behave
the same way.

═══════════════════════════════════════════════════════════════════════════════
MACHINE COLLECTION
═══════════════════════════════════════════════════════════════════════════════

By default TestBench creates two machines:
- ``ActionProductMachine`` (async) with mocks via ``resources``.
- ``SyncActionProductMachine`` (sync) with mocks via ``resources``.

Both machines receive the same plugins and log coordinator. Bench metadata reads
use the stored ``NodeGraphCoordinator``. Terminal ``run`` executes action on EACH
machine and compares results through ``compare_results()``.

═══════════════════════════════════════════════════════════════════════════════
MOCK RESET BETWEEN RUNS
═══════════════════════════════════════════════════════════════════════════════

Method ``run()`` executes action on two machines sequentially. Between async
and sync runs, all ``Mock`` objects (``unittest.mock.Mock``, ``MagicMock``,
``AsyncMock``) are reset via ``reset_mock()``. This guarantees:
- Each machine runs with clean mocks.
- Tests can use ``assert_called_once_with()`` without double-run noise.
- ``call_count`` reflects only calls from the final (sync) run.

Mocks are NOT reset again after both runs; test sees mock state after sync run.

═══════════════════════════════════════════════════════════════════════════════
MOCK PREPARATION
═══════════════════════════════════════════════════════════════════════════════

TestBench prepares mocks through ``_prepare_mock()`` using these rules
(check order matters):

1. ``MockAction`` -> as is (mock action replacement).
2. ``BaseAction`` -> as is (real action instance).
3. ``unittest.mock.Mock`` -> as is (mock object for ``box.resolve()``).
   Includes ``Mock``, ``MagicMock``, ``AsyncMock`` and subclasses.
   Critical rule: ``AsyncMock(spec=PaymentClient)`` is keyed by the declared
   ``@depends`` resource class (e.g. ``PaymentServiceResource``) so
   ``box.resolve(PaymentServiceResource)`` returns the mock or wrapper.
4. ``BaseResult`` -> wrapped in ``MockAction(result=value)``.
5. ``callable`` -> wrapped in ``MockAction(side_effect=value)``.
6. anything else -> as is (for ``box.resolve()``).

Rule 3 is BEFORE rule 5 because ``AsyncMock`` is callable but should not be
wrapped into ``MockAction``; it is intended for ``resolve()``.

═══════════════════════════════════════════════════════════════════════════════
ROLLUP PROPAGATION
═══════════════════════════════════════════════════════════════════════════════

Terminal methods (``run``, ``run_aspect``, ``run_summary``) accept mandatory
``rollup: bool`` without a default value. Test author explicitly chooses mode.

Rollup is forwarded into ``machine._run_internal(rollup=rollup)``, then into
``ToolsBox(rollup=rollup)``. ToolsBox uses rollup in:
- ``resolve()`` -> ``factory.resolve(cls, rollup=rollup)``
- ``run()`` -> ``run_child`` closure forwards rollup recursively.

═══════════════════════════════════════════════════════════════════════════════
COMPENSATOR TESTING
═══════════════════════════════════════════════════════════════════════════════

Method ``run_compensator()`` provides isolated execution of one compensator for
unit testing. It is a compensator analogue of ``run_aspect()``.

Without ``run_compensator()``, compensator testing requires:
1. Build action with several aspects.
2. Mock one aspect to fail.
3. Wait for stack unwind.
4. Verify compensator side effects.
That is an integration test.

With ``run_compensator()`` you can test compensator AS A UNIT: pass ``params``,
``state_before``, ``state_after``, ``error`` directly and assert side effects.

KEY DIFFERENCE FROM PRODUCTION:
``run_compensator()`` DOES NOT suppress exceptions.
In production, ``_rollback_saga()`` suppresses compensator errors.
In tests, errors are propagated, allowing validation that:
- compensator does NOT fail under normal conditions,
- compensator handles internal failures correctly,
- compensator DOES fail in specific edge cases.

API symmetry:

    | Property             | run_aspect()     | run_compensator()        |
    |----------------------|------------------|--------------------------|
    | Target method        | @regular_aspect  | @compensate              |
    | Method lookup        | by name          | by name                  |
    | Marker validation    | _aspect_meta     | _compensate_meta         |
    | Return value         | dict             | None (side effects)      |
    | Errors               | propagated       | propagated               |
    | @context_requires    | supported        | supported                |

═══════════════════════════════════════════════════════════════════════════════
FLUENT API (IMMUTABLE)
═══════════════════════════════════════════════════════════════════════════════

Each fluent method returns a NEW ``TestBench`` instance:

    from action_machine.testing import StubTesterRole

    bench = TestBench(mocks={PaymentServiceResource: mock})
    admin_bench = bench.with_user(user_id="admin", roles=(StubTesterRole,))
    # bench and admin_bench are different objects.
    # bench is unchanged after with_user call.

"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar, cast
from unittest.mock import Mock

from action_machine.auth.base_role import BaseRole
from action_machine.context.context import Context
from action_machine.context.context_view import ContextView
from action_machine.graph_model.nodes.action_graph_node import ActionGraphNode
from action_machine.graph_model.nodes.summary_aspect_graph_node import SummaryAspectGraphNode
from action_machine.logging.domain_resolver import resolve_domain
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.plugin.plugin import Plugin
from action_machine.resources.base_resource import BaseResource
from action_machine.runtime.action_product_machine import ActionProductMachine
from action_machine.runtime.dependency_factory import DependencyFactory
from action_machine.runtime.sync_action_product_machine import SyncActionProductMachine
from action_machine.runtime.tools_box import ToolsBox
from action_machine.system_core import TypeIntrospection
from action_machine.testing.checker_facet_snapshot import CheckerFacetSnapshot
from action_machine.testing.comparison import compare_results
from action_machine.testing.mock_action import MockAction
from action_machine.testing.state_validator import validate_state_for_aspect, validate_state_for_summary
from action_machine.testing.stubs import RequestInfoStub, RuntimeInfoStub, UserInfoStub
from graph.create_node_graph_coordinator import create_node_graph_coordinator
from graph.node_graph_coordinator import NodeGraphCoordinator

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


# ═════════════════════════════════════════════════════════════════════════════
# Constants
# ═════════════════════════════════════════════════════════════════════════════

_COMPENSATE_META_ATTR = "_compensate_meta"
"""
Attribute name written by ``@compensate`` decorator on method.
Used by ``run_compensator()`` to verify the method is a compensator.
"""

_CONTEXT_REQUIRES_ATTR = "_required_context_keys"
"""
Attribute name written by ``@context_requires`` decorator on method.
Used by ``run_compensator()`` to decide whether ``ContextView`` is required.
"""


@dataclass(frozen=True)
class _BenchAspect:
    """Aspect metadata row assembled from the node graph."""

    method_name: str
    aspect_type: str
    description: str
    method_ref: Callable[..., Any]
    context_keys: frozenset[str]


@dataclass(frozen=True)
class _BenchChecker:
    """Checker metadata row consumed by ``testing.state_validator``."""

    method_name: str
    checker_class: type
    field_name: str
    required: bool
    extra_params: dict[str, Any]


# ═════════════════════════════════════════════════════════════════════════════
# Module-level helper functions
# ═════════════════════════════════════════════════════════════════════════════


def _action_node_from_coordinator(
    coordinator: NodeGraphCoordinator,
    action_cls: type,
) -> ActionGraphNode[Any] | None:
    node_id = TypeIntrospection.full_qualname(action_cls)
    try:
        return cast(
            ActionGraphNode[Any],
            coordinator.get_node_by_id(node_id, ActionGraphNode.NODE_TYPE),
        )
    except (LookupError, RuntimeError):
        return None


def _aspect_tuple_from_coordinator(
    coordinator: NodeGraphCoordinator,
    action_cls: type,
) -> tuple[Any, ...]:
    action_node = _action_node_from_coordinator(coordinator, action_cls)
    if action_node is None:
        return ()
    aspects: list[_BenchAspect] = []
    for regular_node in action_node.get_regular_aspect_graph_nodes():
        aspects.append(
            _BenchAspect(
                method_name=regular_node.label,
                aspect_type="regular",
                description=str(regular_node.properties.get("description", "")),
                method_ref=regular_node.node_obj,
                context_keys=regular_node.get_required_context_keys(),
            ),
        )
    for edge in action_node.summary_aspect:
        summary_node = cast(SummaryAspectGraphNode, edge.target_node)
        aspects.append(
            _BenchAspect(
                method_name=summary_node.label,
                aspect_type="summary",
                description=str(summary_node.properties.get("description", "")),
                method_ref=summary_node.node_obj,
                context_keys=summary_node.get_required_context_keys(),
            ),
        )
    return tuple(aspects)


def _dependency_factory_from_coordinator(
    coordinator: NodeGraphCoordinator,
    action_cls: type,
) -> DependencyFactory:
    if _action_node_from_coordinator(coordinator, action_cls) is None:
        return DependencyFactory(())
    return DependencyFactory(tuple(getattr(action_cls, "_depends_info", ()) or ()))


def _checker_rows_from_action_class(
    action_cls: type,
) -> tuple[CheckerFacetSnapshot.Checker, ...]:
    """Build checker facet rows from ``_checker_meta`` on aspect methods."""
    out: list[CheckerFacetSnapshot.Checker] = []
    for attr_name, attr_value in vars(action_cls).items():
        func = TypeIntrospection.unwrap_declaring_class_member(attr_value)
        if not callable(func):
            continue
        checker_list = getattr(func, "_checker_meta", None)
        if checker_list is None:
            continue
        for checker_dict in checker_list:
            out.append(
                CheckerFacetSnapshot.Checker(
                    method_name=attr_name,
                    checker_class=checker_dict.get("checker_class", type(None)),
                    field_name=checker_dict.get("field_name", ""),
                    required=checker_dict.get("required", False),
                    extra_params={
                        k: v
                        for k, v in checker_dict.items()
                        if k not in ("checker_class", "field_name", "required")
                    },
                ),
            )
    return tuple(out)


def _checkers_for_aspect_name(
    coordinator: NodeGraphCoordinator,
    action_cls: type,
    method_name: str,
) -> tuple[Any, ...]:
    action_node = _action_node_from_coordinator(coordinator, action_cls)
    if action_node is None:
        return ()
    out: list[_BenchChecker] = []
    for aspect_node in action_node.get_regular_aspect_graph_nodes():
        if aspect_node.label != method_name:
            continue
        for checker_node in aspect_node.get_checker_graph_nodes():
            payload = checker_node.node_obj
            extra_params = dict(payload.properties)
            extra_params.pop("TypeChecker", None)
            extra_params.pop("required", None)
            out.append(
                _BenchChecker(
                    method_name=payload.aspect_method_name,
                    checker_class=payload.checker_class,
                    field_name=payload.field_name,
                    required=payload.required,
                    extra_params=extra_params,
                ),
            )
    if not out:
        return _checker_rows_from_action_class(action_cls)
    return tuple(out)


def _prepare_mock(value: Any) -> Any:
    """
    Convert mock value into a resource-ready object.

    Order is important: ``Mock`` is checked BEFORE ``callable`` because
    AsyncMock/MagicMock are callable but must pass as direct resources.
    """
    if isinstance(value, MockAction):
        return value
    if isinstance(value, BaseAction):
        return value
    if isinstance(value, Mock):
        return value
    if isinstance(value, BaseResult):
        return MockAction(result=value)
    if callable(value):
        return MockAction(side_effect=value)
    return value


def _prepare_all_mocks(mocks: dict[type, Any]) -> dict[type, Any]:
    """
    Prepare all mocks from mapping through ``_prepare_mock``.
    """
    return {cls: _prepare_mock(val) for cls, val in mocks.items()}


def _reset_mock_tree(value: Any) -> None:
    """
    Clear call history on unittest mocks, including doubles held on resources.

    Handles: bare ``Mock`` / ``AsyncMock``, ``ExternalServiceResource.service``,
    and ``WrapperExternalServiceResource`` chains (``_inner``).
    """
    if isinstance(value, Mock):
        value.reset_mock()
        return
    service = getattr(value, "service", None)
    if isinstance(service, Mock):
        service.reset_mock()
        return
    inner = getattr(value, "_inner", None)
    if inner is not None:
        _reset_mock_tree(inner)


def _reset_all_mocks(mocks: dict[type, Any] | None) -> None:
    """
    Reset state of all unittest mocks reachable from ``mocks`` values.

    Used between async and sync ``TestBench.run()`` so assertions see only the
    final machine's side effects.
    """
    if not mocks:
        return
    for value in mocks.values():
        _reset_mock_tree(value)


# ═════════════════════════════════════════════════════════════════════════════
# TestBench class
# ═════════════════════════════════════════════════════════════════════════════


class TestBench:
    """
    Unified immutable entry point for ActionMachine action testing.
    """

    __test__ = False  # pytest: this is not a test class

    def __init__(
        self,
        coordinator: NodeGraphCoordinator | None = None,
        mocks: dict[type, Any] | None = None,
        plugins: list[Plugin] | None = None,
        log_coordinator: LogCoordinator | None = None,
        user: Any | None = None,
        runtime: Any | None = None,
        request: Any | None = None,
    ) -> None:
        """
        Initialize TestBench.
        """
        self._coordinator = coordinator or create_node_graph_coordinator()
        self._mocks = dict(mocks) if mocks else {}
        self._prepared_mocks = _prepare_all_mocks(self._mocks)
        self._plugins = list(plugins) if plugins else []
        self._log_coordinator = log_coordinator
        self._user = user if user is not None else UserInfoStub()
        self._runtime = runtime if runtime is not None else RuntimeInfoStub()
        self._request = request if request is not None else RequestInfoStub()

    # ─────────────────────────────────────────────────────────────────────
    # Read-only properties
    # ─────────────────────────────────────────────────────────────────────

    @property
    def coordinator(self) -> NodeGraphCoordinator:
        """Node graph coordinator."""
        return self._coordinator

    @property
    def mocks(self) -> dict[type, Any]:
        """Original mocks mapping."""
        return dict(self._mocks)

    @property
    def plugins(self) -> list[Plugin]:
        """Plugin list."""
        return list(self._plugins)

    # ─────────────────────────────────────────────────────────────────────
    # Internal helpers: machine/context construction
    # ─────────────────────────────────────────────────────────────────────

    def _build_context(self) -> Context:
        """Build Context from current user/request/runtime."""
        return Context(
            user=self._user,
            request=self._request,
            runtime=self._runtime,
        )

    def _build_async_machine(self) -> ActionProductMachine:
        """Build async production machine with current settings."""
        kwargs: dict[str, Any] = {
            "plugins": self._plugins,
        }
        if self._log_coordinator is not None:
            kwargs["log_coordinator"] = self._log_coordinator
        return ActionProductMachine(**kwargs)

    def _build_sync_machine(self) -> SyncActionProductMachine:
        """Build sync production machine with current settings."""
        kwargs: dict[str, Any] = {
            "plugins": self._plugins,
        }
        if self._log_coordinator is not None:
            kwargs["log_coordinator"] = self._log_coordinator
        return SyncActionProductMachine(**kwargs)

    # ─────────────────────────────────────────────────────────────────────
    # Fluent API (each method returns NEW TestBench)
    # ─────────────────────────────────────────────────────────────────────

    def _clone(self, **overrides: Any) -> TestBench:
        """Create TestBench copy with overridden fields."""
        return TestBench(
            coordinator=overrides.get("coordinator", self._coordinator),
            mocks=overrides.get("mocks", self._mocks),
            plugins=overrides.get("plugins", self._plugins),
            log_coordinator=overrides.get("log_coordinator", self._log_coordinator),
            user=overrides.get("user", self._user),
            runtime=overrides.get("runtime", self._runtime),
            request=overrides.get("request", self._request),
        )

    def with_user(
        self,
        user_id: str = "test_user",
        roles: tuple[type[BaseRole], ...] | list[type[BaseRole]] | None = None,
        **kwargs: Any,
    ) -> TestBench:
        """Return new TestBench with modified user."""
        return self._clone(user=UserInfoStub(user_id=user_id, roles=roles, **kwargs))

    def with_runtime(
        self,
        hostname: str = "test-host",
        service_name: str = "test-service",
        service_version: str = "0.0.1",
        **kwargs: Any,
    ) -> TestBench:
        """Return new TestBench with modified runtime info."""
        return self._clone(
            runtime=RuntimeInfoStub(
                hostname=hostname,
                service_name=service_name,
                service_version=service_version,
                **kwargs,
            ),
        )

    def with_request(
        self,
        trace_id: str = "test-trace-000",
        request_path: str = "/test",
        protocol: str = "test",
        request_method: str = "TEST",
        **kwargs: Any,
    ) -> TestBench:
        """Return new TestBench with modified request info."""
        return self._clone(
            request=RequestInfoStub(
                trace_id=trace_id,
                request_path=request_path,
                protocol=protocol,
                request_method=request_method,
                **kwargs,
            ),
        )

    def with_mocks(self, mocks: dict[type, Any]) -> TestBench:
        """Return new TestBench with replaced mocks (not merge)."""
        return self._clone(mocks=mocks)

    # ─────────────────────────────────────────────────────────────────────
    # Terminal methods
    # ─────────────────────────────────────────────────────────────────────

    async def run(
        self,
        action: BaseAction[P, R],
        params: P,
        rollup: bool,
        connections: dict[str, BaseResource] | None = None,
    ) -> R:
        """
        Full action run on async and sync machines with result comparison.

        For ``MockAction`` performs direct call without pipeline.
        """
        if isinstance(action, MockAction):
            return cast("R", action.run(params))

        context = self._build_context()

        # Run 1: async machine
        async_machine = self._build_async_machine()
        async_result = await async_machine._run_internal(
            context=context,
            action=action,
            params=params,
            resources=self._prepared_mocks or None,
            connections=connections,
            nested_level=0,
            rollup=rollup,
        )

        # Reset mocks between runs (``_prepared_mocks`` is usually the same
        # instances as ``_mocks``, but reset both maps for robustness).
        _reset_all_mocks(self._mocks)
        _reset_all_mocks(self._prepared_mocks)

        # Run 2: sync machine
        sync_machine = self._build_sync_machine()
        sync_result = await sync_machine._run_internal(
            context=context,
            action=action.__class__(),
            params=params,
            resources=self._prepared_mocks or None,
            connections=connections,
            nested_level=0,
            rollup=rollup,
        )

        compare_results(
            async_result, "AsyncMachine",
            sync_result, "SyncMachine",
        )

        return async_result

    async def run_aspect(
        self,
        action: BaseAction[Any, Any],
        aspect_name: str,
        params: BaseParams,
        state: dict[str, Any],
        rollup: bool,
        connections: dict[str, BaseResource] | None = None,
    ) -> dict[str, Any]:
        """
        Execute one regular aspect with state validation.
        """
        context = self._build_context()
        action_cls = action.__class__
        aspects = _aspect_tuple_from_coordinator(self._coordinator, action_cls)

        def _chk(method_name: str) -> tuple[Any, ...]:
            return _checkers_for_aspect_name(
                self._coordinator, action_cls, method_name,
            )

        validate_state_for_aspect(aspects, _chk, aspect_name, state)

        target_aspect = None
        for aspect_meta in aspects:
            if aspect_meta.method_name == aspect_name:
                target_aspect = aspect_meta
                break

        if target_aspect is None:
            available = [a.method_name for a in aspects]
            raise ValueError(
                f"Aspect '{aspect_name}' not found in {action.__class__.__name__}. "
                f"Available: {available}."
            )

        async_machine = self._build_async_machine()
        factory = _dependency_factory_from_coordinator(self._coordinator, action.__class__)

        log = ScopedLogger(
            coordinator=async_machine._log_coordinator,
            nest_level=1,
            action_name=action.get_full_class_name(),
            aspect_name=aspect_name,
            context=context,
            state=BaseState(**state) if state else BaseState(),
            params=params,
            domain=resolve_domain(action_cls),
        )

        box = ToolsBox(
            run_child=self._make_run_child(async_machine, context, rollup),
            factory=factory,
            resources=self._prepared_mocks or None,
            log=log,
            nested_level=1,
            rollup=rollup,
        )

        base_state = BaseState(**state) if state else BaseState()
        conns = connections or {}

        return cast(
            "dict[str, Any]",
            await target_aspect.method_ref(action, params, base_state, box, conns),
        )

    async def run_summary(
        self,
        action: BaseAction[Any, Any],
        params: BaseParams,
        state: dict[str, Any],
        rollup: bool,
        connections: dict[str, BaseResource] | None = None,
    ) -> BaseResult:
        """
        Execute summary aspect only with full state validation.
        """
        context = self._build_context()
        action_cls = action.__class__
        aspects = _aspect_tuple_from_coordinator(self._coordinator, action_cls)

        def _chk(method_name: str) -> tuple[Any, ...]:
            return _checkers_for_aspect_name(
                self._coordinator, action_cls, method_name,
            )

        validate_state_for_summary(aspects, _chk, state)

        summaries = [a for a in aspects if a.aspect_type == "summary"]
        summary_meta = summaries[0] if summaries else None
        if summary_meta is None:
            raise ValueError(
                f"Action {action.__class__.__name__} has no summary aspect."
            )

        async_machine = self._build_async_machine()
        factory = _dependency_factory_from_coordinator(self._coordinator, action.__class__)

        log = ScopedLogger(
            coordinator=async_machine._log_coordinator,
            nest_level=1,
            action_name=action.get_full_class_name(),
            aspect_name=summary_meta.method_name,
            context=context,
            state=BaseState(**state) if state else BaseState(),
            params=params,
            domain=resolve_domain(action_cls),
        )

        box = ToolsBox(
            run_child=self._make_run_child(async_machine, context, rollup),
            factory=factory,
            resources=self._prepared_mocks or None,
            log=log,
            nested_level=1,
            rollup=rollup,
        )

        base_state = BaseState(**state) if state else BaseState()
        conns = connections or {}

        return cast(
            "BaseResult",
            await summary_meta.method_ref(action, params, base_state, box, conns),
        )

    async def run_compensator(
        self,
        action: BaseAction[Any, Any],
        compensator_name: str,
        *,
        params: BaseParams,
        state_before: BaseState,
        state_after: BaseState | None,
        error: Exception,
        connections: dict[str, BaseResource] | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Isolated compensator execution for unit testing.

        Unlike production rollback, compensator exceptions are propagated.
        """
        action_class = action.__class__
        action_class_name = action_class.__name__

        # 1. Locate method on class
        method = getattr(action_class, compensator_name, None)
        if method is None:
            raise ValueError(
                f"Method '{compensator_name}' not found in {action_class_name}. "
                f"Check method name."
            )

        # 2. Ensure this is a compensator
        if not hasattr(method, _COMPENSATE_META_ATTR):
            raise ValueError(
                f"Method '{compensator_name}' in {action_class_name} is not a "
                f"compensator (missing @compensate decorator). "
                f"Ensure the method is marked with "
                f"@compensate(target_aspect_name, description)."
            )

        # 3. Prepare environment
        ctx = self._build_context()

        async_machine = self._build_async_machine()
        factory = _dependency_factory_from_coordinator(self._coordinator, action_class)

        log = ScopedLogger(
            coordinator=async_machine._log_coordinator,
            nest_level=1,
            action_name=action.get_full_class_name(),
            aspect_name=compensator_name,
            context=ctx,
            state=state_before,
            params=params,
            domain=resolve_domain(action_class),
        )

        box = ToolsBox(
            run_child=self._make_run_child(async_machine, ctx, False),
            factory=factory,
            resources=self._prepared_mocks or None,
            log=log,
            nested_level=1,
            rollup=False,
        )

        conns = connections or {}

        # 4. Handle @context_requires
        context_keys = getattr(method, _CONTEXT_REQUIRES_ATTR, None)

        if context_keys:
            if context is None:
                keys_str = ", ".join(sorted(context_keys))
                raise ValueError(
                    f"Compensator '{compensator_name}' in {action_class_name} "
                    f"uses @context_requires (keys: {keys_str}), "
                    f"but context argument is missing. Pass dict with required "
                    f"context keys."
                )
            ctx_view = ContextView(ctx, frozenset(context_keys))
            await method(
                action, params, state_before, state_after,
                box, conns, error, ctx_view,
            )
        else:
            await method(
                action, params, state_before, state_after,
                box, conns, error,
            )

    # ─────────────────────────────────────────────────────────────────────
    # Helper methods
    # ─────────────────────────────────────────────────────────────────────

    def _make_run_child(
        self,
        machine: ActionProductMachine,
        context: Context,
        rollup: bool,
    ) -> Any:
        """
        Create ``run_child`` closure for ToolsBox.

        Closure delegates child-action execution into machine ``_run_internal``
        with current mocks and rollup.
        """
        prepared = self._prepared_mocks

        async def run_child(
            child_action: BaseAction[Any, Any],
            child_params: BaseParams,
            child_connections: dict[str, BaseResource] | None = None,
        ) -> BaseResult:
            if isinstance(child_action, MockAction):
                return child_action.run(child_params)
            return await machine._run_internal(
                context=context,
                action=child_action,
                params=child_params,
                resources=prepared or None,
                connections=child_connections,
                nested_level=1,
                rollup=rollup,
            )

        return run_child
