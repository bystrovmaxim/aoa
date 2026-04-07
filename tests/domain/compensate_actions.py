# tests/domain/compensate_actions.py
"""
Action с компенсаторами (@compensate) для тестирования механизма Saga.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит Action, демонстрирующие и тестирующие различные сценарии
компенсации (паттерн Saga) при ошибках в конвейере аспектов:

- CompensatedOrderAction — два regular-аспекта с компенсаторами.
  При ошибке в финальном аспекте компенсаторы вызываются в обратном
  порядке. Проверяет базовый механизм размотки стека.

- PartialCompensateAction — три regular-аспекта, компенсатор только
  у первого. Проверяет skipped-фреймы при размотке: аспекты без
  компенсатора пропускаются, но учитываются в счётчиках.

- CompensateErrorAction — компенсатор, который сам бросает RuntimeError.
  Проверяет молчаливое подавление ошибок компенсаторов: размотка
  продолжается, все последующие компенсаторы получают шанс выполниться.

- CompensateAndOnErrorAction — Action с компенсаторами И @on_error.
  Проверяет порядок: сначала размотка стека компенсации, затем
  вызов @on_error. Обработчик @on_error получает ОРИГИНАЛЬНУЮ
  ошибку аспекта, а не ошибку компенсатора.

- CompensateWithContextAction — компенсатор с @context_requires.
  Проверяет интеграцию с ContextView: машина создаёт ContextView
  с разрешёнными ключами и передаёт как 8-й параметр (ctx).

═══════════════════════════════════════════════════════════════════════════════
ВСПОМОГАТЕЛЬНЫЕ СЕРВИСЫ
═══════════════════════════════════════════════════════════════════════════════

- InventoryService — сервис управления запасами. Методы reserve()
  и unreserve(). В тестах заменяется AsyncMock.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА КОМПЕНСАЦИИ
═══════════════════════════════════════════════════════════════════════════════

Компенсатор — async-метод, декорированный @compensate(target_aspect_name,
description). Привязан к конкретному regular-аспекту по строковому имени.
При ошибке в любом аспекте ActionProductMachine разматывает стек
SagaFrame в обратном порядке, вызывая компенсаторы уже выполненных
аспектов.

Сигнатура компенсатора (7 параметров без @context_requires):
    async def name_compensate(self, params, state_before, state_after,
                              box, connections, error)

Сигнатура компенсатора (8 параметров с @context_requires):
    async def name_compensate(self, params, state_before, state_after,
                              box, connections, error, ctx)

Параметры:
    params       — входные параметры действия (frozen BaseParams).
    state_before — состояние ДО выполнения аспекта (frozen BaseState).
    state_after  — состояние ПОСЛЕ аспекта (frozen BaseState или None).
    box          — ToolsBox (тот же экземпляр, что у аспектов).
    connections  — словарь ресурсных менеджеров.
    error        — исключение, вызвавшее размотку стека.
    ctx          — ContextView (только при @context_requires).

Возвращаемое значение компенсатора ИГНОРИРУЕТСЯ.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

    from tests.domain.compensate_actions import (
        CompensatedOrderAction,
        PartialCompensateAction,
        CompensateErrorAction,
        CompensateAndOnErrorAction,
        CompensateWithContextAction,
        InventoryService,
    )

    mock_inventory = AsyncMock(spec=InventoryService)
    mock_inventory.reserve.return_value = "RES-001"
    mock_inventory.unreserve.return_value = True
"""

from typing import Any

from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.checkers import result_float, result_string
from action_machine.compensate import compensate
from action_machine.context import Ctx, context_requires
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.dependencies.depends import depends
from action_machine.on_error import on_error
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .domains import OrdersDomain
from .services import PaymentService


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательный сервис
# ═════════════════════════════════════════════════════════════════════════════


class InventoryService:
    """
    Сервис управления запасами.

    Предоставляет методы reserve() и unreserve(). В production
    обращается к складской системе. В тестах заменяется AsyncMock.
    """

    async def reserve(self, item_id: str, quantity: int) -> str:
        """
        Резервирует товар на складе.

        Аргументы:
            item_id: идентификатор товара.
            quantity: количество для резервирования.

        Возвращает:
            str — идентификатор резервации.
        """
        raise NotImplementedError("InventoryService.reserve() не реализован")

    async def unreserve(self, reservation_id: str) -> bool:
        """
        Отменяет резервацию товара.

        Аргументы:
            reservation_id: идентификатор резервации для отмены.

        Возвращает:
            bool — True если отмена успешна.
        """
        raise NotImplementedError("InventoryService.unreserve() не реализован")


# ═════════════════════════════════════════════════════════════════════════════
# Общие Params и Result для компенсируемых действий
# ═════════════════════════════════════════════════════════════════════════════


class CompensateTestParams(BaseParams):
    """Параметры для тестовых компенсируемых действий."""

    user_id: str = Field(description="Идентификатор пользователя")
    amount: float = Field(description="Сумма заказа", gt=0)
    item_id: str = Field(default="ITEM-001", description="Идентификатор товара")
    should_fail: bool = Field(
        default=False,
        description="Если True — финальный аспект бросит исключение",
    )


class CompensateTestResult(BaseResult):
    """Результат тестовых компенсируемых действий."""

    status: str = Field(description="Статус выполнения")
    detail: str = Field(default="", description="Детали результата")


# ═════════════════════════════════════════════════════════════════════════════
# CompensatedOrderAction — базовый Action с двумя компенсаторами
# ═════════════════════════════════════════════════════════════════════════════


@meta(
    description="Заказ с двумя компенсируемыми шагами: оплата и резервирование",
    domain=OrdersDomain,
)
@check_roles(ROLE_NONE)
@depends(PaymentService, description="Сервис обработки платежей")
@depends(InventoryService, description="Сервис управления запасами")
class CompensatedOrderAction(
    BaseAction[CompensateTestParams, CompensateTestResult],
):
    """
    Action с двумя regular-аспектами, оба имеют компенсаторы.

    Конвейер:
    1. charge_aspect (regular) — списывает средства через PaymentService.
       Компенсатор: rollback_charge_compensate — вызывает refund().
    2. reserve_aspect (regular) — резервирует товар через InventoryService.
       Компенсатор: rollback_reserve_compensate — вызывает unreserve().
    3. finalize_aspect (regular) — если should_fail=True, бросает ValueError.
       Без компенсатора.
    4. build_result_summary (summary) — формирует Result.

    Сценарии тестирования:
    - should_fail=False → нормальный Result(status="ok").
    - should_fail=True → ValueError в finalize_aspect →
      rollback_reserve_compensate (2-й) → rollback_charge_compensate (1-й) →
      ошибка пробрасывается (нет @on_error).
    """

    @regular_aspect("Списание средств")
    @result_string("txn_id", required=True, min_length=1)
    async def charge_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        """Списывает средства через PaymentService."""
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, "RUB")
        return {"txn_id": txn_id}

    @compensate("charge_aspect", "Откат платежа — возврат средств")
    async def rollback_charge_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        """
        Компенсатор для charge_aspect.

        Вызывает refund() на PaymentService с txn_id из state_after.
        Если state_after is None (чекер отклонил) — пропускает откат.
        """
        if state_after is None:
            return
        payment = box.resolve(PaymentService)
        await payment.refund(state_after["txn_id"])

    @regular_aspect("Резервирование товара")
    @result_string("reservation_id", required=True, min_length=1)
    async def reserve_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        """Резервирует товар через InventoryService."""
        inventory = box.resolve(InventoryService)
        reservation_id = await inventory.reserve(params.item_id, 1)
        return {"reservation_id": reservation_id}

    @compensate("reserve_aspect", "Откат резервирования — отмена резерва")
    async def rollback_reserve_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        """
        Компенсатор для reserve_aspect.

        Вызывает unreserve() на InventoryService с reservation_id
        из state_after. Если state_after is None — пропускает.
        """
        if state_after is None:
            return
        inventory = box.resolve(InventoryService)
        await inventory.unreserve(state_after["reservation_id"])

    @regular_aspect("Финализация заказа")
    @result_string("order_id", required=True)
    async def finalize_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        """Финализирует заказ. При should_fail=True — бросает ValueError."""
        if params.should_fail:
            raise ValueError(f"Ошибка финализации для {params.user_id}")
        return {"order_id": f"ORD-{params.user_id}"}

    @summary_aspect("Формирование результата заказа")
    async def build_result_summary(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CompensateTestResult:
        """Формирует итоговый Result из state."""
        return CompensateTestResult(
            status="ok",
            detail=f"order={state['order_id']}, txn={state['txn_id']}",
        )


# ═════════════════════════════════════════════════════════════════════════════
# PartialCompensateAction — компенсатор только у первого аспекта
# ═════════════════════════════════════════════════════════════════════════════


@meta(
    description="Действие с частичной компенсацией — только первый аспект",
    domain=OrdersDomain,
)
@check_roles(ROLE_NONE)
@depends(PaymentService, description="Сервис обработки платежей")
class PartialCompensateAction(
    BaseAction[CompensateTestParams, CompensateTestResult],
):
    """
    Action с тремя regular-аспектами, компенсатор только у первого.

    Тестирует skipped-фреймы при размотке: второй и третий аспекты
    не имеют компенсаторов — их фреймы пропускаются (счётчик skipped
    в SagaRollbackCompletedEvent).

    Конвейер:
    1. charge_aspect (regular, с компенсатором).
    2. log_aspect (regular, БЕЗ компенсатора).
    3. fail_aspect (regular, БЕЗ компенсатора) — бросает ValueError.
    4. build_result_summary (summary).
    """

    @regular_aspect("Списание средств")
    @result_string("txn_id", required=True)
    async def charge_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, "RUB")
        return {"txn_id": txn_id}

    @compensate("charge_aspect", "Откат платежа")
    async def rollback_charge_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        if state_after is None:
            return
        payment = box.resolve(PaymentService)
        await payment.refund(state_after["txn_id"])

    @regular_aspect("Логирование операции")
    @result_string("log_entry", required=True)
    async def log_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        """Логирует операцию. Без компенсатора — лог не откатывается."""
        return {"log_entry": f"charged:{state['txn_id']}"}

    @regular_aspect("Аспект с ошибкой")
    @result_string("final_note", required=True)
    async def fail_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        """Всегда бросает ValueError для тестирования размотки."""
        raise ValueError("Намеренная ошибка для тестирования")

    @summary_aspect("Формирование результата")
    async def build_result_summary(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CompensateTestResult:
        return CompensateTestResult(status="ok")


# ═════════════════════════════════════════════════════════════════════════════
# CompensateErrorAction — компенсатор бросает исключение
# ═════════════════════════════════════════════════════════════════════════════


@meta(
    description="Действие с компенсатором, который сам бросает исключение",
    domain=OrdersDomain,
)
@check_roles(ROLE_NONE)
@depends(PaymentService, description="Сервис обработки платежей")
@depends(InventoryService, description="Сервис управления запасами")
class CompensateErrorAction(
    BaseAction[CompensateTestParams, CompensateTestResult],
):
    """
    Action, чей первый компенсатор бросает RuntimeError.

    Тестирует молчаливое подавление ошибок компенсаторов:
    - rollback_charge_compensate бросает RuntimeError.
    - Размотка ПРОДОЛЖАЕТСЯ — rollback_reserve_compensate вызывается.
    - Ошибка компенсатора доступна через CompensateFailedEvent.
    - Исходная ошибка аспекта (ValueError) пробрасывается наружу.

    Конвейер:
    1. charge_aspect (компенсатор бросает RuntimeError).
    2. reserve_aspect (компенсатор работает нормально).
    3. fail_aspect — бросает ValueError.
    4. build_result_summary.
    """

    @regular_aspect("Списание средств")
    @result_string("txn_id", required=True)
    async def charge_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, "RUB")
        return {"txn_id": txn_id}

    @compensate("charge_aspect", "Откат платежа — бросает ошибку")
    async def rollback_charge_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        """Компенсатор, который НАМЕРЕННО бросает RuntimeError."""
        raise RuntimeError("Платёжный шлюз недоступен при откате")

    @regular_aspect("Резервирование товара")
    @result_string("reservation_id", required=True)
    async def reserve_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        inventory = box.resolve(InventoryService)
        reservation_id = await inventory.reserve(params.item_id, 1)
        return {"reservation_id": reservation_id}

    @compensate("reserve_aspect", "Откат резервирования — работает нормально")
    async def rollback_reserve_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        """Компенсатор, который работает нормально (не бросает)."""
        if state_after is None:
            return
        inventory = box.resolve(InventoryService)
        await inventory.unreserve(state_after["reservation_id"])

    @regular_aspect("Финализация с ошибкой")
    @result_string("order_id", required=True)
    async def fail_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        raise ValueError("Ошибка финализации")

    @summary_aspect("Формирование результата")
    async def build_result_summary(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CompensateTestResult:
        return CompensateTestResult(status="ok")


# ═════════════════════════════════════════════════════════════════════════════
# CompensateAndOnErrorAction — компенсаторы + @on_error
# ═════════════════════════════════════════════════════════════════════════════


@meta(
    description="Действие с компенсаторами и обработчиком @on_error",
    domain=OrdersDomain,
)
@check_roles(ROLE_NONE)
@depends(PaymentService, description="Сервис обработки платежей")
@depends(InventoryService, description="Сервис управления запасами")
class CompensateAndOnErrorAction(
    BaseAction[CompensateTestParams, CompensateTestResult],
):
    """
    Action с компенсаторами И @on_error(ValueError).

    Тестирует порядок обработки ошибки:
    1. fail_aspect бросает ValueError.
    2. _rollback_saga() — размотка стека в обратном порядке
       (rollback_reserve_compensate → rollback_charge_compensate).
    3. _handle_aspect_error() → @on_error(ValueError) → Result.

    @on_error получает ОРИГИНАЛЬНУЮ ошибку аспекта (ValueError),
    а не ошибку компенсатора (даже если компенсатор упал).
    """

    @regular_aspect("Списание средств")
    @result_string("txn_id", required=True)
    async def charge_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, "RUB")
        return {"txn_id": txn_id}

    @compensate("charge_aspect", "Откат платежа")
    async def rollback_charge_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        if state_after is None:
            return
        payment = box.resolve(PaymentService)
        await payment.refund(state_after["txn_id"])

    @regular_aspect("Резервирование товара")
    @result_string("reservation_id", required=True)
    async def reserve_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        inventory = box.resolve(InventoryService)
        reservation_id = await inventory.reserve(params.item_id, 1)
        return {"reservation_id": reservation_id}

    @compensate("reserve_aspect", "Откат резервирования")
    async def rollback_reserve_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> None:
        if state_after is None:
            return
        inventory = box.resolve(InventoryService)
        await inventory.unreserve(state_after["reservation_id"])

    @regular_aspect("Финализация с ошибкой")
    @result_string("order_id", required=True)
    async def fail_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        raise ValueError(f"Ошибка финализации для {params.user_id}")

    @summary_aspect("Формирование результата")
    async def build_result_summary(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CompensateTestResult:
        return CompensateTestResult(status="ok")

    @on_error(ValueError, description="Обработка ошибки финализации")
    async def handle_finalize_on_error(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> CompensateTestResult:
        """
        Обработчик ошибки. Вызывается ПОСЛЕ завершения размотки
        стека компенсации. Получает ОРИГИНАЛЬНУЮ ошибку аспекта.
        """
        return CompensateTestResult(
            status="handled_after_compensate",
            detail=str(error),
        )


# ═════════════════════════════════════════════════════════════════════════════
# CompensateWithContextAction — компенсатор с @context_requires
# ═════════════════════════════════════════════════════════════════════════════


@meta(
    description="Действие с компенсатором, использующим @context_requires",
    domain=OrdersDomain,
)
@check_roles(ROLE_NONE)
@depends(PaymentService, description="Сервис обработки платежей")
class CompensateWithContextAction(
    BaseAction[CompensateTestParams, CompensateTestResult],
):
    """
    Action с компенсатором, который использует @context_requires.

    Компенсатор rollback_charge_compensate декларирует доступ к
    Ctx.User.user_id. Машина создаёт ContextView и передаёт как
    8-й параметр (ctx). Компенсатор вызывает ctx.get(Ctx.User.user_id)
    для логирования.

    Конвейер:
    1. charge_aspect (regular, с компенсатором + @context_requires).
    2. fail_aspect (regular, бросает ValueError).
    3. build_result_summary (summary).
    """

    @regular_aspect("Списание средств")
    @result_string("txn_id", required=True)
    async def charge_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, "RUB")
        return {"txn_id": txn_id}

    @compensate("charge_aspect", "Откат платежа с контекстом")
    @context_requires(Ctx.User.user_id)
    async def rollback_charge_compensate(
        self,
        params: CompensateTestParams,
        state_before: BaseState,
        state_after: BaseState | None,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
        ctx: Any,
    ) -> None:
        """
        Компенсатор с доступом к контексту.

        Использует ctx.get(Ctx.User.user_id) для получения ID
        пользователя. Вызывает refund() на PaymentService.
        """
        user_id = ctx.get(Ctx.User.user_id)
        if state_after is None:
            return
        payment = box.resolve(PaymentService)
        await payment.refund(state_after["txn_id"])

    @regular_aspect("Финализация с ошибкой")
    @result_string("order_id", required=True)
    async def fail_aspect(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        raise ValueError("Ошибка финализации")

    @summary_aspect("Формирование результата")
    async def build_result_summary(
        self,
        params: CompensateTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CompensateTestResult:
        return CompensateTestResult(status="ok")
