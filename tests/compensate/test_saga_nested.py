# tests/compensate/test_saga_nested.py
"""
Тесты вложенных вызовов и изоляции стеков компенсации.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Проверяет архитектурное решение о локальных стеках вложенных вызовов:

- Каждый _run_internal создаёт СВОЙ локальный стек. Глобального стека нет.
- Дочерний Action (через box.run) разматывает СВОЙ стек и пробрасывает
  исключение.
- Если родительский аспект перехватывает ошибку дочернего через try/except,
  для родителя аспект ЗАВЕРШИЛСЯ УСПЕШНО — он добавляется в стек родителя.
- При последующей ошибке в родительском конвейере компенсатор этого
  аспекта будет вызван.
═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА
═══════════════════════════════════════════════════════════════════════════════
TestNestedStacks — изоляция стеков, взаимодействие с try/except
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.checkers import result_string
from action_machine.compensate import compensate
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.dependencies.depends import depends
from action_machine.resource_managers.base_resource_manager import BaseResourceManager
from action_machine.testing import TestBench
from tests.domain_model.domains import TestDomain
from tests.domain_model.services import InventoryService, PaymentService

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные Action для тестов вложенности
# ═════════════════════════════════════════════════════════════════════════════


class NestedParams(BaseParams):
    """Параметры для тестов вложенности."""
    should_child_fail: bool = Field(
        default=False,
        description="Если True — дочернее действие бросит исключение",
    )
    should_parent_fail: bool = Field(
        default=False,
        description="Если True — родительское действие бросит исключение",
    )


class NestedResult(BaseResult):
    """Результат для тестов вложенности."""
    status: str = Field(
        default="ok",
        description="Статус выполнения",
    )


@meta(description="Дочернее действие, которое может упасть", domain=TestDomain)
@check_roles(ROLE_NONE)
@depends(InventoryService, description="Сервис запасов")
class FailableChildAction(BaseAction[NestedParams, NestedResult]):

    @regular_aspect("Резервирование в дочернем")
    @result_string("child_reservation_id", required=True)
    async def reserve_aspect(
        self, params, state, box, connections,
    ) -> dict[str, Any]:
        inventory = box.resolve(InventoryService)
        res_id = await inventory.reserve("CHILD-ITEM", 1)
        return {"child_reservation_id": res_id}

    @compensate("reserve_aspect", "Откат резервирования в дочернем")
    async def rollback_reserve_compensate(
        self, params, state_before, state_after, box, connections, error,
    ) -> None:
        if state_after is None:
            return
        inventory = box.resolve(InventoryService)
        await inventory.unreserve(state_after.child_reservation_id)

    @regular_aspect("Финализация дочернего")
    @result_string("child_final", required=True)
    async def finalize_child_aspect(
        self, params, state, box, connections,
    ) -> dict[str, Any]:
        if params.should_child_fail:
            raise ValueError("Дочерняя ошибка финализации")
        return {"child_final": "done"}

    @summary_aspect("Формирование результата дочернего")
    async def build_result_summary(
        self, params, state, box, connections,
    ) -> NestedResult:
        return NestedResult(status="child_ok")


@meta(description="Родительское действие, вызывающее дочернее через box.run", domain=TestDomain)
@check_roles(ROLE_NONE)
@depends(PaymentService, description="Сервис платежей")
@depends(InventoryService, description="Сервис запасов")
class ParentWithNestedCallAction(BaseAction[NestedParams, NestedResult]):
    """
    Родительское действие с тремя regular-аспектами:
    1. charge_aspect — списание средств (с компенсатором).
    2. call_child_aspect — вызывает FailableChildAction через box.run(),
       оборачивает в try/except. Имеет компенсатор.
    3. finalize_aspect — при should_parent_fail=True бросает ValueError.
       Без компенсатора.
    """

    @regular_aspect("Списание средств в родительском")
    @result_string("parent_txn_id", required=True)
    async def charge_aspect(
        self,
        params: NestedParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(100.0, "RUB")
        return {"parent_txn_id": txn_id}

    @compensate("charge_aspect", "Откат платежа в родительском")
    async def rollback_charge_compensate(
        self,
        params: NestedParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        if state_after is None:
            return
        payment = box.resolve(PaymentService)
        await payment.refund(state_after.parent_txn_id)

    @regular_aspect("Вызов дочернего действия")
    @result_string("child_status", required=True)
    async def call_child_aspect(
        self,
        params: NestedParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        """
        Вызывает FailableChildAction через box.run().
        Оборачивает в try/except: если дочернее упало — возвращает
        fallback-значение. Для родителя аспект завершился УСПЕШНО.
        """
        try:
            child_result = await box.run_child(
                FailableChildAction(),
                params,
            )
            return {"child_status": child_result.status}
        except ValueError:
            return {"child_status": "child_failed_handled"}

    @compensate("call_child_aspect", "Откат вызова дочернего")
    async def rollback_call_child_compensate(
        self,
        params: NestedParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        """
        Компенсатор для call_child_aspect.
        Используем unreserve как маркер вызова компенсатора.
        """
        inventory = box.resolve(InventoryService)
        await inventory.unreserve("PARENT-CHILD-ROLLBACK")

    @regular_aspect("Финализация в родительском")
    @result_string("parent_order_id", required=True)
    async def finalize_aspect(
        self,
        params: NestedParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        if params.should_parent_fail:
            raise ValueError("Ошибка финализации родительского")
        return {"parent_order_id": "PARENT-ORD-001"}

    @summary_aspect("Формирование результата родительского")
    async def build_result_summary(
        self,
        params: NestedParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> NestedResult:
        return NestedResult(status="parent_ok")


# ═════════════════════════════════════════════════════════════════════════════
# TestNestedStacks
# ═════════════════════════════════════════════════════════════════════════════


class TestNestedStacks:
    """
    Проверяет изоляцию стеков компенсации при вложенных вызовах.

    Каждый _run_internal создаёт свой стек. Дочерний разматывает свой,
    родительский — свой. Стеки не пересекаются.
    """

    @pytest.mark.anyio
    async def test_child_stack_isolated_from_parent(
        self,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """
        Дочерний Action разматывает СВОЙ стек при ошибке.
        Родитель перехватывает ошибку через try/except — для родителя
        аспект завершился успешно. Стек родителя не затронут.
        """
        # ── Arrange ──
        bench = TestBench(
            mocks={
                PaymentService: mock_payment,
                InventoryService: mock_inventory,
            },
            log_coordinator=AsyncMock(),
        )

        params = NestedParams(
            should_child_fail=True,
            should_parent_fail=False,
        )

        # ── Act ──
        result = await bench.run(
            ParentWithNestedCallAction(),
            params,
            rollup=False,
        )

        # ── Assert ──
        assert result.status == "parent_ok"

        # Дочерний компенсатор вызвал unreserve (дочерний стек размотан).
        # Родительский компенсатор НЕ вызван (родитель не упал).
        # Используем call_count — TestBench.run() прогоняет две машины.
        assert mock_inventory.unreserve.call_count >= 1
        assert mock_payment.refund.call_count == 0

    @pytest.mark.anyio
    async def test_parent_compensates_after_child_caught(
        self,
        mock_payment: AsyncMock,
        mock_inventory: AsyncMock,
    ) -> None:
        """
        Если дочернее действие упало и родитель перехватил, а затем
        РОДИТЕЛЬ упал — компенсаторы родителя вызываются для всех
        успешных аспектов, включая тот, что перехватил ошибку дочернего.
        """
        # ── Arrange ──
        bench = TestBench(
            mocks={
                PaymentService: mock_payment,
                InventoryService: mock_inventory,
            },
            log_coordinator=AsyncMock(),
        )

        params = NestedParams(
            should_child_fail=True,
            should_parent_fail=True,
        )

        # ── Act ──
        with pytest.raises(ValueError, match="Ошибка финализации родительского"):
            await bench.run(
                ParentWithNestedCallAction(),
                params,
                rollup=False,
            )

        # ── Assert ──
        # unreserve вызван минимум дважды (от каждого прогона машины):
        # 1. Дочерний: unreserve("RES-TEST-001") — размотка дочернего стека.
        # 2. Родительский: unreserve("PARENT-CHILD-ROLLBACK") — размотка родительского.
        # При двух прогонах — удвоение.
        unreserve_args = [c[0][0] for c in mock_inventory.unreserve.call_args_list]
        assert "PARENT-CHILD-ROLLBACK" in unreserve_args

        # refund вызван — родительский компенсатор charge_aspect
        assert mock_payment.refund.call_count >= 1
