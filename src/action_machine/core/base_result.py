# src/action_machine/core/base_result.py
"""
BaseResult — frozen-результат выполнения действия.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

BaseResult — базовый контракт выходных данных ActionMachine.
Экземпляр создаётся summary-аспектом (или обработчиком @on_error)
и возвращается вызывающему коду как финальный результат действия.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- frozen=True: запись в поля после создания запрещена.
- extra="forbid": результат содержит только явно объявленные поля.

    result = OrderResult(order_id="ORD-1", status="created", total=1500.0)
    result.status = "paid"        # → ValidationError

Единственный способ «изменить» результат — создать новый экземпляр:

    updated = result.model_copy(update={"status": "paid"})

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

Summary-аспект создаёт обычный `BaseResult`-наследник:

    @summary_aspect("Формирование result")
    async def build_result_summary(self, params, state, box, connections):
        return OrderResult(
            order_id=f"ORD_{params.user_id}",
            status="created",
            total=state["total"],
        )

@on_error может вернуть альтернативный Result:

    @on_error(ValueError, description="Ошибка валидации")
    async def validation_on_error(self, params, state, box, connections, error):
        return OrderResult(order_id="ERR", status="validation_error", total=0)

Плагины читают Result через event.result, но не могут его изменить.
Адаптеры (FastAPI, MCP) сериализуют через model_dump().

═══════════════════════════════════════════════════════════════════════════════
ОТЛИЧИЕ ОТ BaseParams И BaseState
═══════════════════════════════════════════════════════════════════════════════

    BaseParams  — frozen, extra="forbid". Входные параметры.
    BaseState   — frozen, extra="allow".  Промежуточное state конвейера.
    BaseResult  — frozen, extra="forbid". Результат действия.

Params приходит снаружи и не меняется. State живёт внутри конвейера.
Result формируется summary-аспектом и возвращается вызывающему коду.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field
    from action_machine.core.base_result import BaseResult

    class OrderResult(BaseResult):
        order_id: str = Field(description="ID созданного заказа")
        status: str = Field(description="Статус заказа", examples=["created"])
        total: float = Field(description="Итоговая сумма", ge=0)

    result = OrderResult(order_id="ORD-123", status="created", total=1500.0)

    # Чтение — dict-стиль (унаследовано от BaseSchema):
    result["status"]            # → "created"
    result.resolve("total")     # → 1500.0
    result.keys()               # → ["order_id", "status", "total"]

    # Сериализация:
    result.model_dump()         # → {"order_id": "ORD-123", "status": "created", "total": 1500.0}

    # Запись запрещена (frozen):
    result.status = "paid"      # → ValidationError

    # Лишние поля запрещены (forbid):
    OrderResult(order_id="x", status="y", total=0, unknown="z")  # → ValidationError

    # «Изменение» — создание нового экземпляра:
    updated = result.model_copy(update={"status": "paid"})

    # JSON Schema для FastAPI и MCP:
    OrderResult.model_json_schema()
    # {"properties": {"order_id": {"description": "ID созданного заказа", ...}, ...}}
"""

from pydantic import ConfigDict

from action_machine.core.base_schema import BaseSchema
from action_machine.core.described_fields_intent import DescribedFieldsIntent


class BaseResult(BaseSchema, DescribedFieldsIntent):
    """
    Базовый frozen-результат действия.

    Наследники объявляют итоговые поля и их описания через Field(..., description=...).
    Запись после создания запрещена (frozen=True), лишние поля не допускаются
    (extra="forbid"), описания полей контролирует DescribedFieldsIntent.

    Конкретный Result создаётся наследованием:

        class OrderResult(BaseResult):
            order_id: str = Field(description="ID заказа")
            total: float = Field(description="Итого", ge=0)
            status: str = Field(description="Статус", examples=["created"])
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
