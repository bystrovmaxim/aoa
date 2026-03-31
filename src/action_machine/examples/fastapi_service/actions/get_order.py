# examples/fastapi_service/actions/get_order.py
"""
GetOrderAction — действие получения заказа по идентификатору.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Демонстрирует GET-эндпоинт с path-параметром. FastAPI извлекает order_id
из URL и передаёт его в Params.

═══════════════════════════════════════════════════════════════════════════════
ЭНДПОИНТ
═══════════════════════════════════════════════════════════════════════════════

    GET /api/v1/orders/{order_id}
    Response: {"order_id": "ORD-123", "status": "created", "total": 1500.0}

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕЧАНИЕ
═══════════════════════════════════════════════════════════════════════════════

В реальном приложении данные загружались бы из БД через connections.
В этом примере возвращается заглушка.
"""

from pydantic import Field

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from ..domains import OrdersDomain


class GetOrderParams(BaseParams):
    """
    Параметры запроса заказа.

    order_id извлекается FastAPI из path-параметра URL.
    """
    order_id: str = Field(
        description="Уникальный идентификатор заказа",
        min_length=1,
        examples=["ORD-user_123-001"],
    )


class GetOrderResult(BaseResult):
    """Результат получения заказа."""
    order_id: str = Field(
        description="Идентификатор заказа",
        examples=["ORD-user_123-001"],
    )
    status: str = Field(
        description="Текущий статус заказа",
        examples=["created", "paid", "shipped"],
    )
    total: float = Field(
        description="Итоговая сумма заказа",
        ge=0,
        examples=[1500.0],
    )


@meta(description="Получение заказа по идентификатору", domain=OrdersDomain)
@CheckRoles(CheckRoles.NONE, desc="Доступно без аутентификации (для примера)")
class GetOrderAction(BaseAction[GetOrderParams, GetOrderResult]):
    """
    Действие получения заказа.

    В реальном приложении загружает данные из БД.
    В примере возвращает заглушку с переданным order_id.
    """

    @summary_aspect("Загрузка и возврат данных заказа")
    async def get_order(
        self,
        params: GetOrderParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> GetOrderResult:
        """Возвращает данные заказа (заглушка для примера)."""
        await box.info("Запрос заказа: {%var.order_id}", order_id=params.order_id)

        return GetOrderResult(
            order_id=params.order_id,
            status="created",
            total=1500.0,
        )
