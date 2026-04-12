# src/examples/fastapi_mcp_services/actions/get_order.py
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
ПАТТЕРН ВЛОЖЕННЫХ МОДЕЛЕЙ
═══════════════════════════════════════════════════════════════════════════════

Params и Result определяются как вложенные классы внутри Action.
Описание действия берётся из ``@meta(description=...)``, описание
аспекта — из ``@summary_aspect("...")``.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕЧАНИЕ
═══════════════════════════════════════════════════════════════════════════════

В реальном приложении данные загружались бы из БД через connections.
В этом примере возвращается заглушка.
"""

from pydantic import Field

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import NoneRole, check_roles
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.logging.channel import Channel
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from ..domains import OrdersDomain


@meta(description="Получение заказа по идентификатору", domain=OrdersDomain)
@check_roles(NoneRole)
class GetOrderAction(BaseAction["GetOrderAction.Params", "GetOrderAction.Result"]):

    class Params(BaseParams):
        """
        Параметры запроса заказа.

        order_id извлекается FastAPI из path-параметра URL.
        """
        order_id: str = Field(
            description="Уникальный идентификатор заказа",
            min_length=1,
            examples=["ORD-user_123-001"],
        )

    class Result(BaseResult):
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

    @summary_aspect("Загрузка и возврат данных заказа")
    async def get_order_summary(
        self,
        params: "GetOrderAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> "GetOrderAction.Result":
        await box.info(
            Channel.business,
            "Запрос заказа: {%var.order_id}",
            order_id=params.order_id,
        )

        return GetOrderAction.Result(
            order_id=params.order_id,
            status="created",
            total=1500.0,
        )
