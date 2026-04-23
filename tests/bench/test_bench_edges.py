# tests/bench/test_bench_edges.py
"""
Edge-case tests for ``TestBench`` helpers and mock preparation.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Lock down ``_prepare_mock`` / ``_prepare_all_mocks`` priority rules,
``_reset_all_mocks`` behavior, ``with_mocks`` replacement semantics,
``MockAction`` short-circuit in ``run``, optional ``log_coordinator`` wiring,
and ``_build_context`` / ``_build_sync_machine`` construction.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Raw mock dict
              |
              v
    _prepare_mock(entry)  --priority-->  passthrough | MockAction wrap
              |
              v
    _reset_all_mocks  ->  mock.reset_mock() on mocks and on ``.service`` / ``_inner`` chains

    TestBench.with_mocks  ->  replaces entire prepared map (not merge)

    _build_context  ->  UserInfo / RequestInfo / RuntimeInfo stubs

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``Mock`` / ``AsyncMock`` must pass through before generic callable wrapping.
- Context fluent overrides affect only their slice (user vs request vs runtime).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    uv run pytest tests/bench/test_bench_edges.py -q

Edge case: plain ``dict`` in mocks survives ``_reset_all_mocks`` untouched.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Line references into ``testing/bench.py`` drift across refactors; behavior is
  authoritative.

═══════════════════════════════════════════════════════════════════════════════
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.resources.external_service.wrapper_external_service_resource import (
    WrapperExternalServiceResource,
)
from action_machine.testing.bench import (
    TestBench,
    _prepare_all_mocks,
    _prepare_mock,
    _reset_all_mocks,
)
from action_machine.testing.mock_action import MockAction, MockActionResult
from tests.scenarios.domain_model import PingAction
from tests.scenarios.domain_model.roles import AdminRole
from tests.scenarios.domain_model.services import PaymentService, PaymentServiceResource

# ═════════════════════════════════════════════════════════════════════════════
# _prepare_mock — rule priority
# ═════════════════════════════════════════════════════════════════════════════


class TestPrepareMock:
    """Verify _prepare_mock applies rules in correct priority order."""

    def test_mock_action_passthrough(self) -> None:
        """Rule 1: MockAction instances are returned unchanged."""
        mock_action = MockAction(result=MockActionResult())
        assert _prepare_mock(mock_action) is mock_action

    def test_base_action_passthrough(self) -> None:
        """Rule 2: BaseAction subclass instances are returned unchanged."""
        action = PingAction()
        assert _prepare_mock(action) is action

    def test_unittest_mock_passthrough(self) -> None:
        """Rule 3: unittest.mock.Mock is returned unchanged (not wrapped)."""
        mock = Mock()
        assert _prepare_mock(mock) is mock

    def test_magic_mock_passthrough(self) -> None:
        """Rule 3: MagicMock is returned unchanged."""
        mock = MagicMock()
        assert _prepare_mock(mock) is mock

    def test_async_mock_passthrough(self) -> None:
        """Rule 3: AsyncMock is returned unchanged (despite being callable)."""
        mock = AsyncMock(spec=PaymentService)
        result = _prepare_mock(mock)
        assert result is mock
        assert not isinstance(result, MockAction)

    def test_base_result_wrapped(self) -> None:
        """Rule 4: BaseResult is wrapped in MockAction(result=value)."""
        br = BaseResult()
        result = _prepare_mock(br)
        assert isinstance(result, MockAction)
        assert result.result is br

    def test_callable_wrapped(self) -> None:
        """Rule 5: Plain callable is wrapped in MockAction(side_effect=value)."""
        fn = lambda p: BaseResult()  # noqa: E731
        result = _prepare_mock(fn)
        assert isinstance(result, MockAction)
        assert result.side_effect is fn

    def test_other_object_passthrough(self) -> None:
        """Rule 6: Any other object is returned unchanged."""
        obj = {"key": "value"}
        assert _prepare_mock(obj) is obj

    def test_string_passthrough(self) -> None:
        """Rule 6: A string is returned unchanged."""
        assert _prepare_mock("hello") == "hello"

    def test_integer_passthrough(self) -> None:
        """Rule 6: An integer is returned unchanged."""
        assert _prepare_mock(42) == 42


# ═════════════════════════════════════════════════════════════════════════════
# _prepare_all_mocks
# ═════════════════════════════════════════════════════════════════════════════


class TestPrepareAllMocks:
    """Verify _prepare_all_mocks processes all entries."""

    def test_processes_all_entries(self) -> None:
        """Each entry in the dict is processed through _prepare_mock."""
        mock_payment = AsyncMock(spec=PaymentService)
        result_obj = BaseResult()

        prepared = _prepare_all_mocks({
            PaymentServiceResource: mock_payment,
            str: result_obj,
        })

        assert prepared[PaymentServiceResource] is mock_payment
        assert isinstance(prepared[str], MockAction)

    def test_empty_dict(self) -> None:
        """Empty dict returns empty dict."""
        assert _prepare_all_mocks({}) == {}


# ═════════════════════════════════════════════════════════════════════════════
# _reset_all_mocks
# ═════════════════════════════════════════════════════════════════════════════


class TestResetAllMocks:
    """Verify mock reset between machine runs."""

    def test_resets_mock_objects(self) -> None:
        """Mock objects have reset_mock called."""
        mock = AsyncMock(spec=PaymentService)
        mock.charge.return_value = "TXN-001"
        # Call count is tracked even without awaiting
        mock.charge.call_count = 1

        _reset_all_mocks({PaymentServiceResource: mock})

        assert mock.charge.call_count == 0

    def test_skips_non_mock_objects(self) -> None:
        """Non-Mock objects in the dict are not affected."""
        plain = {"key": "value"}
        _reset_all_mocks({str: plain})

        assert plain == {"key": "value"}

    def test_mixed_dict(self) -> None:
        """Dict with both Mock and non-Mock is handled correctly."""
        mock = AsyncMock()
        mock.some_method.call_count = 1

        _reset_all_mocks({
            PaymentServiceResource: mock,
            str: "plain_value",
            int: 42,
        })

        assert mock.some_method.call_count == 0

    def test_resets_asyncmock_inside_external_service_resource(self) -> None:
        """``PaymentServiceResource(mock)`` — reset targets the client on ``.service``."""
        client = AsyncMock(spec=PaymentService)
        client.refund.call_count = 1
        _reset_all_mocks({PaymentServiceResource: PaymentServiceResource(client)})
        assert client.refund.call_count == 0

    def test_resets_through_wrapper_external_service_resource(self) -> None:
        """Nested wrapper delegates ``.service`` to the same client mock."""
        client = AsyncMock(spec=PaymentService)
        root = PaymentServiceResource(client)
        wrapped = WrapperExternalServiceResource(root)
        wrapped.service.refund.call_count = 1
        _reset_all_mocks({PaymentServiceResource: wrapped})
        assert client.refund.call_count == 0


# ═════════════════════════════════════════════════════════════════════════════
# TestBench.with_mocks — replacement, not merge
# ═════════════════════════════════════════════════════════════════════════════


class TestWithMocksReplacement:
    """Verify with_mocks replaces the entire mocks dict."""

    def test_replaces_mocks(self) -> None:
        """with_mocks replaces mocks completely, original is unchanged."""
        mock1 = AsyncMock(spec=PaymentService)
        bench = TestBench(mocks={PaymentServiceResource: mock1})

        mock2 = AsyncMock()
        new_bench = bench.with_mocks({str: mock2})

        assert PaymentServiceResource in bench.mocks
        assert str not in bench.mocks

        assert str in new_bench.mocks
        assert PaymentServiceResource not in new_bench.mocks


# ═════════════════════════════════════════════════════════════════════════════
# TestBench.run with MockAction — direct bypass
# ═════════════════════════════════════════════════════════════════════════════


class TestRunMockAction:
    """Verify that MockAction is called directly without machine pipeline."""

    @pytest.mark.asyncio
    async def test_mock_action_bypasses_machine(self) -> None:
        """MockAction.run() is called directly, machine is not involved."""
        expected = PingAction.Result(message="mocked_pong")
        mock_action = MockAction(result=expected)

        bench = TestBench()
        result = await bench.run(mock_action, BaseParams(), rollup=False)

        assert result is expected
        assert mock_action.call_count == 1

    @pytest.mark.asyncio
    async def test_mock_action_with_side_effect(self) -> None:
        """MockAction with side_effect computes result from params."""
        mock_action = MockAction(
            side_effect=lambda p: PingAction.Result(message="computed"),
        )

        bench = TestBench()
        result = await bench.run(mock_action, BaseParams(), rollup=False)

        assert result.message == "computed"


# ═════════════════════════════════════════════════════════════════════════════
# TestBench — log_coordinator passthrough
# ═════════════════════════════════════════════════════════════════════════════


class TestBenchLogCoordinator:
    """Verify log_coordinator is passed to machines."""

    def test_none_log_coordinator(self) -> None:
        """When log_coordinator is None, bench creates machines without it."""
        bench = TestBench(log_coordinator=None)
        machine = bench._build_async_machine()
        assert machine is not None

    def test_custom_log_coordinator(self) -> None:
        """Custom log_coordinator is passed to the machine."""
        from action_machine.logging.log_coordinator import LogCoordinator
        log_coord = LogCoordinator()

        bench = TestBench(log_coordinator=log_coord)
        machine = bench._build_async_machine()
        assert machine is not None


# ═════════════════════════════════════════════════════════════════════════════
# TestBench._build_context
# ═════════════════════════════════════════════════════════════════════════════


class TestBuildContext:
    """Verify context construction from bench attributes."""

    def test_default_context(self) -> None:
        """Default bench creates a valid context."""
        bench = TestBench()
        ctx = bench._build_context()

        assert ctx.user.user_id == "test_user"
        assert ctx.request.trace_id == "test-trace-000"
        assert ctx.runtime.hostname == "test-host"

    def test_context_after_with_user(self) -> None:
        """with_user changes only the user in the context."""
        bench = TestBench().with_user(user_id="admin", roles=(AdminRole,))
        ctx = bench._build_context()

        assert ctx.user.user_id == "admin"
        assert ctx.user.roles == (AdminRole,)
        assert ctx.request.trace_id == "test-trace-000"

    def test_context_after_with_request(self) -> None:
        """with_request changes only the request in the context."""
        bench = TestBench().with_request(trace_id="custom-trace")
        ctx = bench._build_context()

        assert ctx.request.trace_id == "custom-trace"
        assert ctx.user.user_id == "test_user"

    def test_context_after_with_runtime(self) -> None:
        """with_runtime changes only the runtime in the context."""
        bench = TestBench().with_runtime(hostname="prod-01")
        ctx = bench._build_context()

        assert ctx.runtime.hostname == "prod-01"
        assert ctx.user.user_id == "test_user"


# ═════════════════════════════════════════════════════════════════════════════
# TestBench._build_sync_machine
# ═════════════════════════════════════════════════════════════════════════════


class TestBuildSyncMachine:
    """Verify sync machine construction."""

    def test_builds_sync_machine(self) -> None:
        """_build_sync_machine returns a SyncActionProductMachine."""
        from action_machine.runtime.sync_action_product_machine import SyncActionProductMachine

        bench = TestBench()
        machine = bench._build_sync_machine()

        assert isinstance(machine, SyncActionProductMachine)

    def test_sync_machine_with_log_coordinator(self) -> None:
        """Sync machine receives the log_coordinator if provided."""
        from action_machine.logging.log_coordinator import LogCoordinator

        log_coord = LogCoordinator()
        bench = TestBench(log_coordinator=log_coord)
        machine = bench._build_sync_machine()

        assert machine is not None
