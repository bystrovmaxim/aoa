# src/examples/fastapi_mcp_services/actions/create_order.py
"""
CreateOrderAction — действие создания заказа.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Демонстрирует создание действия с валидацией входных параметров через
Pydantic Field constraints. Constraints автоматически попадают в OpenAPI
schema и проверяются FastAPI при десериализации запроса.

═══════════════════════════════════════════════════════════════════════════════
ЭНДПОИНТ
═══════════════════════════════════════════════════════════════════════════════

    POST /api/v1/orders
    Body: {"user_id": "user_123", "amount": 1500.0, "currency": "RUB"}
    Response: {"order_id": "ORD-user_123-001", "status": "created", "total": 1500.0}

═══════════════════════════════════════════════════════════════════════════════
ВАЛИДАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

- user_id: строка, минимум 1 символ.
- amount: float, строго больше 0 (gt=0).
- currency: строка из 3 заглавных латинских букв (pattern=^[A-Z]{3}$).

При нарушении constraints FastAPI автоматически возвращает 422
с описанием ошибки валидации.

═══════════════════════════════════════════════════════════════════════════════
ПАТТЕРН ВЛОЖЕННЫХ МОДЕЛЕЙ
═══════════════════════════════════════════════════════════════════════════════

Params и Result определяются как вложенные классы внутри Action.
Описание действия берётся из ``@meta(description=...)``, описания
аспектов — из ``@regular_aspect("...")`` и ``@summary_aspect("...")``.

Действие содержит один regular-аспект (валидация) с чекером
``@result_string`` и один summary-аспект (формирование результата).
"""

from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.checkers import result_string
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from ..domains import OrdersDomain


@meta(description="Создание нового заказа", domain=OrdersDomain)
@check_roles(ROLE_NONE)
class CreateOrderAction(BaseAction["CreateOrderAction.Params", "CreateOrderAction.Result"]):

    class Params(BaseParams):
        """
        Параметры создания заказа.

        Каждое поле описано через Field(description=...) — описания попадают
        в OpenAPI schema автоматически. Constraints (gt, min_length, pattern)
        проверяются Pydantic при десериализации и отображаются в Swagger UI.
        """
        user_id: str = Field(
            description="Идентификатор пользователя, создающего заказ",
            min_length=1,
            examples=["user_123"],
        )
        amount: float = Field(
            description="Сумма заказа в указанной валюте. Должна быть положительной",
            gt=0,
            examples=[1500.0, 99.99],
        )
        currency: str = Field(
            default="RUB",
            description="Код валюты в формате ISO 4217 (3 заглавные буквы)",
            pattern=r"^[A-Z]{3}$",
            examples=["RUB", "USD", "EUR"],
        )

    class Result(BaseResult):
        """Результат создания заказа."""
        order_id: str = Field(
            description="Уникальный идентификатор созданного заказа",
            examples=["ORD-user_123-001"],
        )
        status: str = Field(
            description="Статус заказа после создания",
            examples=["created"],
        )
        total: float = Field(
            description="Итоговая сумма заказа",
            ge=0,
            examples=[1500.0],
        )

    @regular_aspect("Валидация данных заказа")
    @result_string("validated_user", required=True)
    async def validate(
        self,
        params: "CreateOrderAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict:
        await box.info(
            "Валидация заказа: пользователь={%var.user_id}, сумма={%var.amount}",
            user_id=params.user_id,
            amount=params.amount,
        )
        return {"validated_user": params.user_id}

    @summary_aspect("Формирование результата создания заказа")
    async def build_result(
        self,
        params: "CreateOrderAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> "CreateOrderAction.Result":
        order_id = f"ORD-{state['validated_user']}-001"

        await box.info("Заказ создан: {%var.order_id}", order_id=order_id)

        return CreateOrderAction.Result(
            order_id=order_id,
            status="created",
            total=params.amount,
        )
