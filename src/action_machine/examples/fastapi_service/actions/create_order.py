# examples/fastapi_service/actions/create_order.py
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
    Response: {"order_id": "ORD-user_123-...", "status": "created", "total": 1500.0}

═══════════════════════════════════════════════════════════════════════════════
ВАЛИДАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

- user_id: строка, минимум 1 символ.
- amount: float, строго больше 0 (gt=0).
- currency: строка из 3 заглавных латинских букв (pattern=^[A-Z]{3}$).

При нарушении constraints FastAPI автоматически возвращает 422
с описанием ошибки валидации.
"""


from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.checkers.result_string_checker import ResultStringChecker
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from ..domains import OrdersDomain


class CreateOrderParams(BaseParams):
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


class CreateOrderResult(BaseResult):
    """
    Результат создания заказа.

    Содержит идентификатор созданного заказа, его статус и итоговую сумму.
    """
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


@meta(description="Создание нового заказа", domain=OrdersDomain)
@CheckRoles(CheckRoles.NONE, desc="Доступно без аутентификации (для примера)")
class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):
    """
    Действие создания заказа.

    Содержит один regular-аспект (валидация) и один summary-аспект
    (формирование результата). Демонстрирует работу чекеров
    на regular-аспекте.
    """

    @regular_aspect("Валидация данных заказа")
    @ResultStringChecker("validated_user", "Проверенный ID пользователя", required=True)
    async def validate(
        self,
        params: CreateOrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict:
        """
        Валидирует входные данные и возвращает проверенный user_id.

        В реальном приложении здесь может быть проверка существования
        пользователя в БД, проверка лимитов и т.д.
        """
        await box.info(
            "Валидация заказа: пользователь={%var.user_id}, сумма={%var.amount}",
            user_id=params.user_id,
            amount=params.amount,
        )
        return {"validated_user": params.user_id}

    @summary_aspect("Формирование результата создания заказа")
    async def build_result(
        self,
        params: CreateOrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> CreateOrderResult:
        """
        Формирует результат на основе параметров и данных из state.

        В реальном приложении здесь создаётся запись в БД,
        отправляется событие в очередь и т.д.
        """
        order_id = f"ORD-{state['validated_user']}-001"

        await box.info("Заказ создан: {%var.order_id}", order_id=order_id)

        return CreateOrderResult(
            order_id=order_id,
            status="created",
            total=params.amount,
        )
