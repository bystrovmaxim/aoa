# tests/compensate/test_bench_run_compensator.py
"""
Тесты метода TestBench.run_compensator() — изолированный запуск компенсаторов.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Проверяет, что TestBench.run_compensator() позволяет тестировать
компенсаторы как unit — без запуска полного конвейера аспектов
и без размотки стека.

Ключевое отличие от production: run_compensator() НЕ ПОДАВЛЯЕТ
исключения. В production _rollback_saga() подавляет ошибки
компенсаторов. В тестах ошибки ПРОБРАСЫВАЮТСЯ — это позволяет
тестировать граничные случаи.
═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА
═══════════════════════════════════════════════════════════════════════════════
TestRunCompensatorBasic       — базовый запуск и проверка побочных эффектов
TestRunCompensatorValidation  — валидации: несуществующий метод, не-компенсатор,
                                отсутствие context
TestRunCompensatorContext     — интеграция с @context_requires
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import Field

from action_machine.dependencies.depends_decorator import depends
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth import NoneRole, check_roles
from action_machine.intents.checkers import result_string
from action_machine.intents.compensate import compensate
from action_machine.intents.context import Ctx, context_requires
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.runtime.machines.core_action_machine import CoreActionMachine
from action_machine.testing import StubTesterRole, TestBench
from tests.domain_model.compensate_actions import (
    CompensatedOrderAction,
    CompensateTestParams,
    CompensateWithContextAction,
)
from tests.domain_model.domains import TestDomain
from tests.domain_model.services import InventoryService, PaymentService

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательная функция для создания BaseState с данными
# ═════════════════════════════════════════════════════════════════════════════


def make_state(**kwargs: Any) -> BaseState:
    """
    Создаёт BaseState с произвольными полями.
    BaseState наследует Pydantic BaseModel и не принимает позиционный dict.
    Используем model_construct() для создания экземпляра с произвольными
    данными без валидации — аналогично тому, как машина создаёт state
    из результатов аспектов.
    """
    state = BaseState.model_construct()
    for key, value in kwargs.items():
        state.__dict__[key] = value
    return state


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательный Action для теста контекста в компенсаторе
# ═════════════════════════════════════════════════════════════════════════════


class CtxCheckParams(BaseParams):
    """Параметры для Action проверки контекста."""
    amount: float = Field(default=1.0, description="Сумма для тестового компенсатора")


class CtxCheckResult(BaseResult):
    """Результат для Action проверки контекста."""
    status: str = Field(default="ok", description="Статус выполнения")


@meta(description="Action для проверки контекста в компенсаторе", domain=TestDomain)
@check_roles(NoneRole)
@depends(PaymentService, description="Платежи")
class CtxCheckAction(BaseAction[CtxCheckParams, CtxCheckResult]):
    """
    Action, чей компенсатор использует ctx.get(Ctx.User.user_id)
    и передаёт user_id в аргумент refund — для проверки, что
    ContextView создаётся с правильными значениями.
    """

    @regular_aspect("Аспект")
    @result_string("txn_id", required=True)
    async def charge_aspect(self, params, state, box, connections):
        return {"txn_id": "TXN-001"}

    @compensate("charge_aspect", "Откат с контекстом")
    @context_requires(Ctx.User.user_id)
    async def rollback_compensate(
        self, params, state_before, state_after, box, connections, error, ctx,
    ):
        user_id = ctx.get(Ctx.User.user_id)
        payment = box.resolve(PaymentService)
        await payment.refund(f"refund_for_{user_id}")

    @summary_aspect("Саммари")
    async def summary(self, params, state, box, connections):
        return CtxCheckResult()


# ═════════════════════════════════════════════════════════════════════════════
# TestRunCompensatorBasic — базовый запуск
# ═════════════════════════════════════════════════════════════════════════════


class TestRunCompensatorBasic:
    """
    Проверяет базовый запуск компенсатора через run_compensator():
    побочные эффекты через моки, проброс ошибок, state_after=None.
    """

    @pytest.mark.anyio
    async def test_compensator_calls_refund_via_mock(
        self,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """
        Изолированный запуск компенсатора — проверка побочного эффекта
        через мок. refund() вызывается с txn_id из state_after.
        """
        # ── Arrange ──
        mock_payment.refund.reset_mock()

        bench = TestBench(
            coordinator=CoreActionMachine.create_coordinator(),
            mocks={
                PaymentService: mock_payment,
                InventoryService: mock_inventory,
            },
            log_coordinator=AsyncMock(),
        )

        params = CompensateTestParams(
            user_id="user_unit",
            amount=100.0,
            item_id="ITEM-U01",
        )
        state_before = BaseState()
        state_after = make_state(txn_id="TXN-UNIT-001")
        error = ValueError("Тестовая ошибка")

        # ── Act ──
        await bench.run_compensator(
            action=CompensatedOrderAction(),
            compensator_name="rollback_charge_compensate",
            params=params,
            state_before=state_before,
            state_after=state_after,
            error=error,
        )

        # ── Assert ──
        mock_payment.refund.assert_awaited_once_with("TXN-UNIT-001")

    @pytest.mark.anyio
    async def test_compensator_error_propagated_in_test(
        self,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """
        В отличие от production, run_compensator() НЕ подавляет ошибки.
        Если компенсатор бросает — исключение пробрасывается.
        """
        # ── Arrange ──
        mock_payment.refund.side_effect = RuntimeError("Шлюз недоступен")

        bench = TestBench(
            coordinator=CoreActionMachine.create_coordinator(),
            mocks={
                PaymentService: mock_payment,
                InventoryService: mock_inventory,
            },
            log_coordinator=AsyncMock(),
        )

        params = CompensateTestParams(
            user_id="user_err",
            amount=100.0,
        )
        state_before = BaseState()
        state_after = make_state(txn_id="TXN-ERR-001")
        error = ValueError("Исходная ошибка")

        # ── Act & Assert ──
        with pytest.raises(RuntimeError, match="Шлюз недоступен"):
            await bench.run_compensator(
                action=CompensatedOrderAction(),
                compensator_name="rollback_charge_compensate",
                params=params,
                state_before=state_before,
                state_after=state_after,
                error=error,
            )

    @pytest.mark.anyio
    async def test_compensator_with_state_after_none(
        self,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """
        Когда state_after=None (чекер отклонил результат аспекта),
        компенсатор получает None и может решить не откатывать.
        CompensatedOrderAction.rollback_charge_compensate пропускает
        refund() при state_after=None.
        """
        # ── Arrange ──
        mock_payment.refund.reset_mock()

        bench = TestBench(
            coordinator=CoreActionMachine.create_coordinator(),
            mocks={
                PaymentService: mock_payment,
                InventoryService: mock_inventory,
            },
            log_coordinator=AsyncMock(),
        )

        params = CompensateTestParams(
            user_id="user_none",
            amount=100.0,
        )
        state_before = BaseState()
        error = ValueError("Чекер отклонил")

        # ── Act ──
        await bench.run_compensator(
            action=CompensatedOrderAction(),
            compensator_name="rollback_charge_compensate",
            params=params,
            state_before=state_before,
            state_after=None,
            error=error,
        )

        # ── Assert ──
        mock_payment.refund.assert_not_awaited()


# ═════════════════════════════════════════════════════════════════════════════
# TestRunCompensatorValidation — валидации
# ═════════════════════════════════════════════════════════════════════════════


class TestRunCompensatorValidation:
    """
    Проверяет валидации run_compensator(): несуществующий метод,
    метод без @compensate, отсутствие context для @context_requires.
    """

    @pytest.mark.anyio
    async def test_nonexistent_method_raises_value_error(self) -> None:
        """
        Несуществующий метод → ValueError с понятным сообщением.
        """
        # ── Arrange ──
        bench = TestBench(
            coordinator=CoreActionMachine.create_coordinator(),
            log_coordinator=AsyncMock(),
        )

        params = CompensateTestParams(user_id="u", amount=1.0)
        state_before = BaseState()
        error = ValueError("test")

        # ── Act & Assert ──
        with pytest.raises(ValueError, match="не найден"):
            await bench.run_compensator(
                action=CompensatedOrderAction(),
                compensator_name="nonexistent_method",
                params=params,
                state_before=state_before,
                state_after=None,
                error=error,
            )

    @pytest.mark.anyio
    async def test_non_compensator_method_raises_value_error(self) -> None:
        """
        Метод без декоратора @compensate → ValueError.
        charge_aspect — это regular-аспект, не компенсатор.
        """
        # ── Arrange ──
        bench = TestBench(
            coordinator=CoreActionMachine.create_coordinator(),
            log_coordinator=AsyncMock(),
        )

        params = CompensateTestParams(user_id="u", amount=1.0)
        state_before = BaseState()
        error = ValueError("test")

        # ── Act & Assert ──
        # bench.run_compensator проверяет наличие _compensate_meta.
        # Если метод найден, но не является компенсатором —
        # сообщение может быть "не является компенсатором" или "не найден".
        with pytest.raises(ValueError):
            await bench.run_compensator(
                action=CompensatedOrderAction(),
                compensator_name="charge_aspect",
                params=params,
                state_before=state_before,
                state_after=None,
                error=error,
            )

    @pytest.mark.anyio
    async def test_context_requires_without_context_raises_value_error(self) -> None:
        """
        Компенсатор с @context_requires, но context не передан → ValueError.
        CompensateWithContextAction.rollback_charge_compensate требует
        Ctx.User.user_id — без контекста запуск невозможен.
        """
        # ── Arrange ──
        mock_payment = AsyncMock(spec=PaymentService)
        bench = TestBench(
            coordinator=CoreActionMachine.create_coordinator(),
            mocks={PaymentService: mock_payment},
            log_coordinator=AsyncMock(),
        )

        params = CompensateTestParams(user_id="u", amount=1.0)
        state_before = BaseState()
        state_after = make_state(txn_id="TXN-001")
        error = ValueError("test")

        # ── Act & Assert ──
        with pytest.raises(ValueError, match="контекст"):
            await bench.run_compensator(
                action=CompensateWithContextAction(),
                compensator_name="rollback_charge_compensate",
                params=params,
                state_before=state_before,
                state_after=state_after,
                error=error,
            )


# ═════════════════════════════════════════════════════════════════════════════
# TestRunCompensatorContext — интеграция с @context_requires
# ═════════════════════════════════════════════════════════════════════════════


class TestRunCompensatorContext:
    """
    Проверяет, что run_compensator() корректно создаёт ContextView
    и передаёт его компенсатору с @context_requires.
    """

    @pytest.mark.anyio
    async def test_context_view_created_with_correct_keys(self) -> None:
        """
        ContextView создаётся с ключами из @context_requires.
        ctx.get(Ctx.User.user_id) возвращает значение из переданного context.
        """
        # ── Arrange ──
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.refund.reset_mock()

        bench = TestBench(
            coordinator=CoreActionMachine.create_coordinator(),
            mocks={PaymentService: mock_payment},
            log_coordinator=AsyncMock(),
        ).with_user(user_id="ctx_user_99", roles=(StubTesterRole,))

        params = CompensateTestParams(
            user_id="ctx_user_99",
            amount=100.0,
        )
        state_before = BaseState()
        state_after = make_state(txn_id="TXN-CTX-001")
        error = ValueError("Тестовая ошибка")

        # ── Act ──
        await bench.run_compensator(
            action=CompensateWithContextAction(),
            compensator_name="rollback_charge_compensate",
            params=params,
            state_before=state_before,
            state_after=state_after,
            error=error,
            context={"user.user_id": "ctx_user_99"},
        )

        # ── Assert ──
        mock_payment.refund.assert_awaited_once_with("TXN-CTX-001")

    @pytest.mark.anyio
    async def test_context_values_accessible_in_compensator(self) -> None:
        """
        Компенсатор с @context_requires получает ctx с правильными
        значениями. CtxCheckAction.rollback_compensate записывает
        user_id из контекста в аргумент refund для проверки.
        """
        # ── Arrange ──
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.refund.reset_mock()

        # with_user() устанавливает user_id в контексте машины.
        # run_compensator() использует этот контекст для создания
        # ContextView, а не аргумент context=.
        bench = TestBench(
            coordinator=CoreActionMachine.create_coordinator(),
            mocks={PaymentService: mock_payment},
            log_coordinator=AsyncMock(),
        ).with_user(user_id="verified_user_42", roles=(StubTesterRole,))

        # ── Act ──
        await bench.run_compensator(
            action=CtxCheckAction(),
            compensator_name="rollback_compensate",
            params=CtxCheckParams(),
            state_before=BaseState(),
            state_after=make_state(txn_id="TXN-001"),
            error=ValueError("test"),
            context={"user.user_id": "verified_user_42"},
        )

        # ── Assert ──
        # refund вызван с user_id из контекста
        mock_payment.refund.assert_awaited_once_with("refund_for_verified_user_42")
