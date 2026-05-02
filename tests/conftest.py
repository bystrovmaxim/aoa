# tests/conftest.py
"""
Shared fixtures for the whole ``tests/`` package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides ready-made fixtures for common needs: metadata coordinator, service
mocks, and ``TestBench`` variants. Everything is built on the shared domain under
``tests/scenarios/domain_model/``.

═══════════════════════════════════════════════════════════════════════════════
PRINCIPLES
═══════════════════════════════════════════════════════════════════════════════

1. Each fixture builds a **new** instance — tests stay isolated.
2. Service mocks use defaults that satisfy domain action checkers.
3. ``TestBench`` fixtures cover: no mocks, with mocks, and mocks plus role.

═══════════════════════════════════════════════════════════════════════════════
MOCK DEFAULTS
═══════════════════════════════════════════════════════════════════════════════

mock_payment.charge() -> "TXN-TEST-001"
    Satisfies ``result_string("txn_id", required=True, min_length=1)``.
    Used in smoke and bench tests for ``txn_id``.

mock_payment.refund() -> True
    Compensators call ``refund()`` on payment rollback. ``True`` means rollback succeeded.

mock_notification.send() -> True
    Notification treated as sent. Smoke tests assert
    ``send("user_42", "Order created: TXN-TEST-001")``.

mock_inventory.reserve() -> "RES-TEST-001"
    Satisfies ``result_string("reservation_id", required=True, min_length=1)``.
    Used in compensation tests for ``reservation_id``.

mock_inventory.unreserve() -> True
    Compensators call ``unreserve()`` when undoing a reservation. ``True`` means success.

═══════════════════════════════════════════════════════════════════════════════
FIXTURES
═══════════════════════════════════════════════════════════════════════════════

coordinator        — fresh ``GraphCoordinator`` per test.

mock_payment       — ``AsyncMock(spec=PaymentService)``, charge -> "TXN-TEST-001",
                     refund -> True.
mock_notification  — ``AsyncMock(spec=NotificationService)``, send -> True.
mock_inventory     — ``AsyncMock(spec=InventoryService)``, reserve -> "RES-TEST-001",
                     unreserve -> True.
mock_db            — ``AsyncMock(spec=OrdersDbManager)``.

clean_bench        — ``TestBench`` without mocks; logging silenced.
bench              — ``TestBench`` with Payment + Notification mocks.
compensate_bench   — ``TestBench`` with Payment + Inventory mocks (compensation).
manager_bench      — bench with ``ManagerRole`` (for ``FullAction``).
admin_bench        — bench with ``AdminRole`` (for ``AdminAction``).
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.testing import TestBench
from graph.graph_coordinator import GraphCoordinator

from .scenarios.domain_model import OrdersDbManager
from .scenarios.domain_model.roles import AdminRole, ManagerRole
from .scenarios.domain_model.services import (
    InventoryService,
    InventoryServiceResource,
    NotificationService,
    NotificationServiceResource,
    PaymentService,
    PaymentServiceResource,
)


@pytest.fixture
def coordinator() -> GraphCoordinator:
    """Built coordinator with default inspectors (same graph as production helpers)."""
    from action_machine.legacy.core import Core

    return Core.create_coordinator()


@pytest.fixture
def mock_payment() -> AsyncMock:
    """
    ``PaymentService`` mock with default behavior.

    ``charge()`` returns ``"TXN-TEST-001"`` — satisfies
    ``result_string("txn_id", required=True, min_length=1)``.

    ``refund()`` returns ``True`` — compensators call it on payment rollback.
    ``refund`` exists on ``PaymentService``, so ``AsyncMock(spec=...)`` exposes it.
    """
    mock = AsyncMock(spec=PaymentService)
    mock.charge.return_value = "TXN-TEST-001"
    mock.refund.return_value = True
    return mock


@pytest.fixture
def mock_notification() -> AsyncMock:
    """
    ``NotificationService`` mock with default behavior.

    ``send()`` returns ``True`` (notification considered sent).
    """
    mock = AsyncMock(spec=NotificationService)
    mock.send.return_value = True
    return mock


@pytest.fixture
def mock_inventory() -> AsyncMock:
    """
    ``InventoryService`` mock with default behavior.

    ``reserve()`` returns ``"RES-TEST-001"`` — satisfies
    ``result_string("reservation_id", required=True, min_length=1)``.

    ``unreserve()`` returns ``True`` — compensators call it when undoing a reservation.
    """
    mock = AsyncMock(spec=InventoryService)
    mock.reserve.return_value = "RES-TEST-001"
    mock.unreserve.return_value = True
    return mock


@pytest.fixture
def mock_db() -> AsyncMock:
    """
    ``OrdersDbManager`` mock for ``connections={"db": mock_db}``.

    Used with ``FullAction``, which declares ``@connection(OrdersDbManager, key="db")``.
    """
    return AsyncMock(spec=OrdersDbManager)


@pytest.fixture
def clean_bench() -> TestBench:
    """
    ``TestBench`` without mocks — for actions without injected dependencies.

    Logging is silenced via ``AsyncMock`` so ``ConsoleLogger`` does not flood output.
    """
    return TestBench(log_coordinator=AsyncMock())


@pytest.fixture
def bench(
    mock_payment: AsyncMock,
    mock_notification: AsyncMock,
) -> TestBench:
    """
    ``TestBench`` with ``PaymentService`` and ``NotificationService`` mocks.

    Default user: ``user_id="test_user"``, ``roles=(StubTesterRole,)``.
    For role-specific actions use ``manager_bench`` or ``admin_bench``.
    """
    return TestBench(
        mocks={
            PaymentServiceResource: PaymentServiceResource(mock_payment),
            NotificationServiceResource: NotificationServiceResource(mock_notification),
        },
        log_coordinator=AsyncMock(),
    )


@pytest.fixture
def compensate_bench(
    mock_payment: AsyncMock,
    mock_inventory: AsyncMock,
) -> TestBench:
    """
    ``TestBench`` with ``PaymentService`` and ``InventoryService`` mocks.

    Intended for compensation (saga) tests. Includes both services used by
    ``CompensatedOrderAction``, ``CompensateErrorAction``,
    ``CompensateAndOnErrorAction``, and ``CompensateWithContextAction``.

    Default user: ``user_id="test_user"``, ``roles=(StubTesterRole,)``.
    Compensating actions use ``NoneRole``, so the default user is sufficient.
    """
    return TestBench(
        mocks={
            PaymentServiceResource: PaymentServiceResource(mock_payment),
            InventoryServiceResource: InventoryServiceResource(mock_inventory),
        },
        log_coordinator=AsyncMock(),
    )


@pytest.fixture
def manager_bench(bench: TestBench) -> TestBench:
    """
    ``TestBench`` with ``ManagerRole`` — for ``FullAction``.

    ``FullAction`` requires ``ManagerRole``; this bench sets a user with that role.
    """
    return bench.with_user(user_id="mgr_1", roles=(ManagerRole,))


@pytest.fixture
def admin_bench(bench: TestBench) -> TestBench:
    """
    ``TestBench`` with ``AdminRole`` — for ``AdminAction``.

    ``AdminAction`` requires ``AdminRole``; this bench sets a user with that role.
    """
    return bench.with_user(user_id="admin_1", roles=(AdminRole,))
