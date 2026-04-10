# tests/bench/test_scratch_vs_coordinator_machine.py
"""
Сравнение ActionProductMachine (scratch) и CoordinatorActionProductMachine.

- Эквивалентность результатов _run_internal() на одном координаторе.
- Сравнение ``_ActionExecutionCache`` scratch vs coordinator.
- Грубый замер времени построения кеша (без жёстких порогов в CI).
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock

import pytest

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.action_product_machine import (
    ActionProductMachine,
    _ActionExecutionCache,
)
from action_machine.core.coordinator_action_product_machine import (
    CoordinatorActionProductMachine,
)
from action_machine.logging.log_coordinator import LogCoordinator
from tests.domain_model import FullAction, NotificationService, PaymentService


def _make_log_coordinator() -> LogCoordinator:
    return LogCoordinator(loggers=[AsyncMock()])


@pytest.mark.anyio
async def test_run_full_action_equivalent_scratch_vs_coordinator(
    coordinator,
    mock_payment: AsyncMock,
    mock_notification: AsyncMock,
    mock_db: AsyncMock,
) -> None:
    """Один и тот же FullAction на двух машинах даёт одинаковый результат."""
    mocks = {PaymentService: mock_payment, NotificationService: mock_notification}
    log = _make_log_coordinator()
    scratch_m = ActionProductMachine(
        mode="test",
        coordinator=coordinator,
        log_coordinator=log,
    )
    coord_m = CoordinatorActionProductMachine(
        mode="test",
        coordinator=coordinator,
        log_coordinator=log,
    )
    ctx = Context(user=UserInfo(user_id="mgr_1", roles=["manager"]))
    action = FullAction()
    params = FullAction.Params(user_id="u1", amount=500.0)
    connections = {"db": mock_db}

    r1 = await scratch_m._run_internal(
        context=ctx,
        action=action,
        params=params,
        resources=mocks,
        connections=connections,
        nested_level=0,
        rollup=False,
    )
    r2 = await coord_m._run_internal(
        context=ctx,
        action=action,
        params=params,
        resources=mocks,
        connections=connections,
        nested_level=0,
        rollup=False,
    )

    assert r1.model_dump() == r2.model_dump()


def test_execution_cache_equivalent_for_full_action(coordinator) -> None:
    """Два способа сборки кеша дают эквивалентные структуры для FullAction."""
    a = _ActionExecutionCache.from_action_class(
        FullAction,
        gate_coordinator=coordinator,
    )
    b = _ActionExecutionCache.from_coordinator_facets(
        FullAction,
        gate_coordinator=coordinator,
    )
    assert a == b


def test_benchmark_execution_cache_build(coordinator) -> None:
    """
    Печатает время N итераций сборки кеша (scratch vs coordinator).

    Запуск с ``pytest -s`` чтобы увидеть строки ``BENCH ...`` в stdout.
    Не проверяет «кто быстрее» — только что оба пути выполнимы.
    """
    n = 1000
    t0 = time.perf_counter()
    for _ in range(n):
        _ActionExecutionCache.from_action_class(
            FullAction,
            gate_coordinator=coordinator,
        )
    scratch_s = time.perf_counter() - t0

    t1 = time.perf_counter()
    for _ in range(n):
        _ActionExecutionCache.from_coordinator_facets(
            FullAction,
            gate_coordinator=coordinator,
        )
    coord_s = time.perf_counter() - t1

    print(
        f"BENCH _ActionExecutionCache FullAction x{n}: "
        f"scratch={scratch_s:.4f}s coordinator={coord_s:.4f}s",
    )
    assert scratch_s > 0
    assert coord_s > 0
