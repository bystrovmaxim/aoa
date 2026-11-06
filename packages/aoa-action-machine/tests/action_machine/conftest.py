# tests/action_machine/conftest.py
"""
Shared fixtures for ``tests/action_machine/`` (and nested subtrees).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Provides ready-made fixtures for common needs: service mocks and ``TestBench``
variants. Everything is built on the shared domain under
``tests/action_machine/scenarios/domain_model/``.

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

mock_payment       — ``AsyncMock(spec=PaymentClient)``, charge -> "TXN-TEST-001",
                     refund -> True.
mock_notification  — ``AsyncMock(spec=NotificationClient)``, send -> True.
mock_inventory     — ``AsyncMock(spec=InventoryClient)``, reserve -> "RES-TEST-001",
                     unreserve -> True.
mock_db            — ``AsyncMock(spec=OrdersStorage)``.

clean_bench        — ``TestBench`` without mocks; logging silenced.
bench              — ``TestBench`` with Payment + Notification mocks.
compensate_bench   — ``TestBench`` with Payment + Inventory mocks (compensation).
manager_bench      — bench with ``ManagerRole`` (for ``FullAction``).
admin_bench        — bench with ``AdminRole`` (for ``AdminAction``).
"""

from unittest.mock import AsyncMock

import pytest

from aoa.action_machine.testing import TestBench

from ..support.domain_model import OrdersStorage
from ..support.domain_model.roles import AdminRole, ManagerRole
from ..support.domain_model.services import (
    InventoryClient,
    InventoryGateway,
    NotificationClient,
    NotificationGateway,
    PaymentClient,
    PaymentGateway,
)


@pytest.fixture
def mock_payment() -> AsyncMock:
    """
    ``PaymentClient`` mock with default behavior.

    ``charge()`` returns ``"TXN-TEST-001"`` — satisfies
    ``result_string("txn_id", required=True, min_length=1)``.

    ``refund()`` returns ``True`` — compensators call it on payment rollback.
    ``refund`` exists on ``PaymentClient``, so ``AsyncMock(spec=...)`` exposes it.
    """
    mock = AsyncMock(spec=PaymentClient)
    mock.charge.return_value = "TXN-TEST-001"
    mock.refund.return_value = True
    return mock


@pytest.fixture
def mock_notification() -> AsyncMock:
    """
    ``NotificationClient`` mock with default behavior.

    ``send()`` returns ``True`` (notification considered sent).
    """
    mock = AsyncMock(spec=NotificationClient)
    mock.send.return_value = True
    return mock


@pytest.fixture
def mock_inventory() -> AsyncMock:
    """
    ``InventoryClient`` mock with default behavior.

    ``reserve()`` returns ``"RES-TEST-001"`` — satisfies
    ``result_string("reservation_id", required=True, min_length=1)``.

    ``unreserve()`` returns ``True`` — compensators call it when undoing a reservation.
    """
    mock = AsyncMock(spec=InventoryClient)
    mock.reserve.return_value = "RES-TEST-001"
    mock.unreserve.return_value = True
    return mock


@pytest.fixture
def mock_db() -> AsyncMock:
    """
    ``OrdersStorage`` mock for ``connections={"db": mock_db}``.

    Used with ``FullAction``, which declares ``@connection(OrdersStorage, key="db")``.
    """
    return AsyncMock(spec=OrdersStorage)


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
    ``TestBench`` with ``PaymentClient`` and ``NotificationClient`` mocks.

    Default user: ``user_id="test_user"``, ``roles=(StubTesterRole,)``.
    For role-specific actions use ``manager_bench`` or ``admin_bench``.
    """
    return TestBench(
        mocks={
            PaymentGateway: PaymentGateway(mock_payment),
            NotificationGateway: NotificationGateway(mock_notification),
        },
        log_coordinator=AsyncMock(),
    )


@pytest.fixture
def compensate_bench(
    mock_payment: AsyncMock,
    mock_inventory: AsyncMock,
) -> TestBench:
    """
    ``TestBench`` with ``PaymentClient`` and ``InventoryClient`` mocks.

    Intended for compensation (saga) tests. Includes both services used by
    ``CompensatedOrderAction``, ``CompensateAndOnErrorAction``, and
    ``CompensateWithContextAction``.

    Default user: ``user_id="test_user"``, ``roles=(StubTesterRole,)``.
    Compensating actions use ``GuestRole``, so the default user is sufficient.
    """
    return TestBench(
        mocks={
            PaymentGateway: PaymentGateway(mock_payment),
            InventoryGateway: InventoryGateway(mock_inventory),
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
