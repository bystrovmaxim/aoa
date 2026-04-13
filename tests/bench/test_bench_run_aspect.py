# tests/bench/test_bench_run_aspect.py
"""
Тесты TestBench.run_aspect() — выполнение одного regular-аспекта.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Первый аспект принимает пустой state (нет предшествующих чекеров).
- Второй аспект с корректным state от первого — выполняется.
- Невалидный state (отсутствует обязательное поле) отклоняется ДО выполнения.
- State с неверным типом поля отклоняется ДО выполнения.
- Несуществующий аспект — StateValidationError.

Все тесты используют FullAction из tests/domain/, который имеет
два regular-аспекта: process_payment_aspect (txn_id) и calc_total_aspect (total).

Все core-типы (Params, Result, State) — неизменяемы. State передаётся как
словарь, аспект возвращает словарь, машина создаёт новый frozen BaseState.
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.testing import TestBench
from action_machine.testing.state_validator import StateValidationError
from tests.scenarios.domain_model import FullAction


class TestFirstAspect:
    """Первый аспект принимает пустой state."""

    @pytest.mark.anyio
    async def test_empty_state_accepted(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """
        process_payment_aspect — первый аспект FullAction. Перед ним нет
        аспектов → нет чекеров для проверки → пустой state допустим.
        """
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        result = await manager_bench.run_aspect(
            action, "process_payment_aspect", params,
            state={},
            rollup=False,
            connections={"db": mock_db},
        )

        # Аспект вернул dict с txn_id
        assert "txn_id" in result
        assert result["txn_id"] == "TXN-TEST-001"


class TestSecondAspect:
    """Второй аспект зависит от полей первого."""

    @pytest.mark.anyio
    async def test_valid_state_from_first_aspect(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """
        calc_total_aspect — второй аспект. Требует txn_id от process_payment_aspect.
        Передаём корректный state — аспект выполняется.
        """
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=250.0)

        result = await manager_bench.run_aspect(
            action, "calc_total_aspect", params,
            state={"txn_id": "TXN-001"},
            rollup=False,
            connections={"db": mock_db},
        )

        # Аспект вернул dict с total
        assert result["total"] == 250.0


class TestInvalidState:
    """Невалидный state отклоняется ДО выполнения аспекта."""

    @pytest.mark.anyio
    async def test_missing_required_field(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """
        calc_total_aspect ожидает txn_id от process_payment_aspect. Пустой state —
        StateValidationError с указанием отсутствующего поля.
        """
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        with pytest.raises(StateValidationError, match="txn_id"):
            await manager_bench.run_aspect(
                action, "calc_total_aspect", params,
                state={},
                rollup=False,
                connections={"db": mock_db},
            )

    @pytest.mark.anyio
    async def test_wrong_type_in_state(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """
        txn_id=123 вместо строки — чекер ResultStringChecker отклоняет
        до выполнения аспекта.
        """
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        with pytest.raises(StateValidationError, match="должен быть строкой"):
            await manager_bench.run_aspect(
                action, "calc_total_aspect", params,
                state={"txn_id": 123},
                rollup=False,
                connections={"db": mock_db},
            )


class TestNonexistentAspect:
    """Несуществующий аспект — понятная ошибка."""

    @pytest.mark.anyio
    async def test_raises_state_validation_error(
        self, manager_bench: TestBench, mock_db: AsyncMock,
    ) -> None:
        """
        Аспект "nonexistent" не найден в FullAction.
        StateValidationError с перечислением доступных аспектов.
        """
        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=100.0)

        with pytest.raises(StateValidationError, match="не найден"):
            await manager_bench.run_aspect(
                action, "nonexistent", params,
                state={},
                rollup=False,
                connections={"db": mock_db},
            )
