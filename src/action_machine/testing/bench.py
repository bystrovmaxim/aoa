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

Both machines receive same coordinator, plugins, and log_coordinator.
Terminal methods (``run``, ``run_aspect``, ``run_summary``) execute action on
EACH machine and compare results through ``compare_results()``.

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
   Critical rule: ``AsyncMock(spec=PaymentService)`` is passed directly into
   ``resources`` so ``box.resolve(PaymentService)`` returns the mock.
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

    bench = TestBench(mocks={PaymentService: mock})
    admin_bench = bench.with_user(user_id="admin", roles=(StubTesterRole,))
    # bench and admin_bench are different objects.
    # bench is unchanged after with_user call.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from unittest.mock import AsyncMock
    from action_machine.testing import TestBench

    mock_payment = AsyncMock(spec=PaymentService)
    mock_payment.charge.return_value = "TXN-001"

    from action_machine.testing import StubTesterRole

    bench = TestBench(mocks={PaymentService: mock_payment})
    admin_bench = bench.with_user(user_id="admin", roles=(StubTesterRole,))

    result = await admin_bench.run(
        CreateOrderAction(),
        OrderParams(user_id="u1", amount=100.0),
        rollup=False,
    )

    # assert_called_once_with works correctly:
    # mocks are reset between async and sync runs,
    # test sees state only from sync run.
    mock_payment.charge.assert_called_once_with(100.0, "RUB")

═══════════════════════════════════════════════════════════════════════════════
COMPENSATOR TESTING EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    async def test_payment_compensator_calls_refund():
        mock_payment = AsyncMock(spec=PaymentService)
        bench = TestBench(mocks={PaymentService: mock_payment})

        await bench.run_compensator(
            action=CreateOrderAction(),
            compensator_name="rollback_payment_compensate",
            params=CreateOrderParams(user_id="u1", items=[...]),
            state_before=CreateOrderState(),
            state_after=CreateOrderState(txn_id="txn_123", amount=100),
            error=InsufficientStockError("Out of stock"),
        )

        mock_payment.refund.assert_called_once_with("txn_123")

    async def test_payment_compensator_handles_unavailable():
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.refund.side_effect = PaymentServiceUnavailable()
        bench = TestBench(mocks={PaymentService: mock_payment})

        # Compensator handles internal error and does not raise
        await bench.run_compensator(
            action=CreateOrderAction(),
            compensator_name="rollback_payment_compensate",
            params=CreateOrderParams(user_id="u1", items=[...]),
            state_before=CreateOrderState(),
            state_after=CreateOrderState(txn_id="txn_456"),
            error=ValueError("some error"),
        )
"""

from __future__ import annotations

from typing import Any, TypeVar, cast
from unittest.mock import Mock

from action_machine.dependencies.dependency_factory import cached_dependency_factory
from action_machine.graph.gate_coordinator import GateCoordinator
from action_machine.intents.auth.base_role import BaseRole
from action_machine.intents.context.context import Context
from action_machine.intents.context.context_view import ContextView
from action_machine.intents.logging.domain_resolver import resolve_domain
from action_machine.intents.logging.log_coordinator import LogCoordinator
from action_machine.intents.logging.scoped_logger import ScopedLogger
from action_machine.intents.plugins.plugin import Plugin
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.machines.action_product_machine import ActionProductMachine
from action_machine.runtime.machines.sync_action_product_machine import SyncActionProductMachine
from action_machine.runtime.tools_box import ToolsBox
from action_machine.testing.comparison import compare_results
from action_machine.testing.mock_action import MockAction
from action_machine.testing.state_validator import validate_state_for_aspect, validate_state_for_summary
from action_machine.testing.stubs import RequestInfoStub, RuntimeInfoStub, UserInfoStub

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


# ═════════════════════════════════════════════════════════════════════════════
# Module-level helper functions
# ═════════════════════════════════════════════════════════════════════════════


def _aspect_tuple_from_coordinator(
    coordinator: GateCoordinator,
    action_cls: type,
) -> tuple[Any, ...]:
    snap = coordinator.get_snapshot(action_cls, "aspect")
    if snap is None or not hasattr(snap, "aspects"):
        return ()
    return tuple(snap.aspects)


def _checkers_for_aspect_name(
    coordinator: GateCoordinator,
    action_cls: type,
    method_name: str,
) -> tuple[Any, ...]:
    snap = coordinator.get_snapshot(action_cls, "checker")
    if snap is None or not hasattr(snap, "checkers"):
        return ()
    return tuple(c for c in snap.checkers if c.method_name == method_name)


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


def _reset_all_mocks(mocks: dict[type, Any]) -> None:
    """
    Reset state of all ``Mock`` objects in mapping.
    """
    for value in mocks.values():
        if isinstance(value, Mock):
            value.reset_mock()


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
        coordinator: GateCoordinator | None = None,
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
        self._coordinator = coordinator or GateCoordinator()
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
    def coordinator(self) -> GateCoordinator:
        """Metadata/factory coordinator."""
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
            "mode": "test",
            "plugins": self._plugins,
        }
        if self._log_coordinator is not None:
            kwargs["log_coordinator"] = self._log_coordinator
        return ActionProductMachine(**kwargs)

    def _build_sync_machine(self) -> SyncActionProductMachine:
        """Build sync production machine with current settings."""
        kwargs: dict[str, Any] = {
            "mode": "test",
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
        connections: dict[str, BaseResourceManager] | None = None,
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

        # Reset mocks between runs
        _reset_all_mocks(self._mocks)

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
        connections: dict[str, BaseResourceManager] | None = None,
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
        factory = cached_dependency_factory(self._coordinator, action.__class__)

        log = ScopedLogger(
            coordinator=async_machine._log_coordinator,
            nest_level=1,
            machine_name="TestBench",
            mode="test",
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
        connections: dict[str, BaseResourceManager] | None = None,
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
        factory = cached_dependency_factory(self._coordinator, action.__class__)

        log = ScopedLogger(
            coordinator=async_machine._log_coordinator,
            nest_level=1,
            machine_name="TestBench",
            mode="test",
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
        connections: dict[str, BaseResourceManager] | None = None,
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
        factory = cached_dependency_factory(self._coordinator, action_class)

        log = ScopedLogger(
            coordinator=async_machine._log_coordinator,
            nest_level=1,
            machine_name="TestBench",
            mode="test",
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
            child_connections: dict[str, BaseResourceManager] | None = None,
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
