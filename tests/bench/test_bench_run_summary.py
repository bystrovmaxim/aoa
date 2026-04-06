# tests/bench/test_bench_run_summary.py
"""
Тесты TestBench.run_summary() — выполнение только summary-аспекта.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Полный state со всеми полями — summary выполняется и возвращает Result.
- Неполный state (отсутствуют поля от regular-аспектов) — отклоняется.
- State с неверным типом поля — отклоняется.
- Действие без regular-аспектов (PingAction) принимает пустой state.
- rollup — обязательный параметр без дефолта.

FullAction имеет два regular-аспекта:
- process_payment → txn_id (string, required)
- calc_total_aspect → total (float, required, min_value=0.0)

Summary build_result читает txn_id и total из state.
Все core-типы (Params, Result, State) — неизменяемы.
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.testing import TestBench
from action_machine.testing.state_validator import StateValidationError
from tests.domain import FullAction, PingAction


class TestCompleteState:
    """Summary выполняется с полным state."""

    @pytest.mark.anyio
    async def test_returns_result_from_state(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """
        build_result читает txn_id и total из state и формирует
        FullAction.Result с order_id, txn_id, total, status.
        """
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=300.0)
        state = {
            "txn_id": "TXN-300",
            "total": 300.0,
        }

        result = await manager_bench.run_summary(
            action, params, state=state,
            rollup=False, connections={"db": mock_db},
        )

        assert result.order_id == "ORD-u1"
        assert result.txn_id == "TXN-300"
        assert result.total == 300.0
        assert result.status == "created"


class TestIncompleteState:
    """Неполный state отклоняется до выполнения summary."""

    @pytest.mark.anyio
    async def test_missing_second_aspect_fields(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """
        state содержит только txn_id от process_payment, но не
        содержит total от calc_total_aspect. Валидатор обнаруживает
        отсутствующее поле и указывает аспект-источник.
        """
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        with pytest.raises(StateValidationError, match="от аспекта 'calc_total_aspect'"):
            await manager_bench.run_summary(
                action, params,
                state={"txn_id": "TXN-1"},
                rollup=False, connections={"db": mock_db},
            )

    @pytest.mark.anyio
    async def test_missing_first_aspect_fields(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """
        state не содержит txn_id от process_payment.
        Ошибка указывает на аспект process_payment.
        """
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        with pytest.raises(StateValidationError, match="txn_id"):
            await manager_bench.run_summary(
                action, params,
                state={"total": 100.0},
                rollup=False, connections={"db": mock_db},
            )


class TestWrongTypeInState:
    """State с неверным типом поля отклоняется."""

    @pytest.mark.anyio
    async def test_total_wrong_type(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """
        total="строка" вместо float — чекер ResultFloatChecker
        отклоняет до выполнения summary.
        """
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        with pytest.raises(StateValidationError, match="total"):
            await manager_bench.run_summary(
                action, params,
                state={"txn_id": "TXN-1", "total": "не число"},
                rollup=False, connections={"db": mock_db},
            )


class TestSummaryOnlyAction:
    """Действие без regular-аспектов принимает пустой state."""

    @pytest.mark.anyio
    async def test_ping_accepts_empty_state(
        self, clean_bench: TestBench,
    ) -> None:
        """
        PingAction не имеет regular-аспектов — нечего валидировать.
        Пустой state допустим.
        """
        action = PingAction()
        params = PingAction.Params()

        result = await clean_bench.run_summary(
            action, params, state={}, rollup=False,
        )

        assert result.message == "pong"


class TestRollupRequired:
    """rollup — обязательный параметр."""

    @pytest.mark.anyio
    async def test_missing_rollup_raises_type_error(
        self, clean_bench: TestBench,
    ) -> None:
        """
        Вызов run_summary() без rollup — TypeError.
        """
        action = PingAction()
        params = PingAction.Params()

        with pytest.raises(TypeError):
            await clean_bench.run_summary(  # type: ignore[call-arg]
                action, params, state={},
            )
