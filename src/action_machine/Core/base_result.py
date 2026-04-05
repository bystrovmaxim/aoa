# src/action_machine/core/base_result.py
"""
BaseResult — frozen-результат выполнения действия.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseResult — базовый класс для всех результатов действий в системе
ActionMachine. Наследует pydantic BaseModel для валидации типов,
описания полей и генерации JSON Schema.

Результат полностью неизменяем после создания (frozen=True). Summary-аспект
создаёт экземпляр Result с конкретными полями, обработчик @on_error
создаёт альтернативный экземпляр. После создания — никаких мутаций.

═══════════════════════════════════════════════════════════════════════════════
FROZEN-СЕМАНТИКА
═══════════════════════════════════════════════════════════════════════════════

Pydantic с ``frozen=True`` запрещает любую запись после создания:

    result = OrderResult(order_id="ORD-1", status="created", total=1500.0)
    result.status = "paid"        # → ValidationError
    result["status"] = "paid"     # → TypeError (нет __setitem__)

Единственный способ «изменить» результат — создать новый экземпляр:

    updated = result.model_copy(update={"status": "paid"})

Или через конструктор:

    new_result = OrderResult(order_id=result.order_id, status="paid", total=result.total)

═══════════════════════════════════════════════════════════════════════════════
СТРОГАЯ СТРУКТУРА (extra="forbid")
═══════════════════════════════════════════════════════════════════════════════

Результат содержит ровно те поля, которые объявлены в конкретном
наследнике. Произвольные поля запрещены — установлен ``extra="forbid"``.
Это обеспечивает:

- Предсказуемость: результат имеет фиксированную структуру, известную
  на этапе определения класса.
- Типобезопасность: mypy и IDE видят все поля, автодополняют,
  проверяют типы.
- Защита от разрастания: нельзя дописать ``result["debug"] = "info"``
  в рантайме. Если нужно дополнительное поле — объявляй в классе.

Если конкретному Result требуется произвольная типизация поля,
используйте ``dict`` или ``Any`` в объявлении:

    class DebugResult(BaseResult):
        order_id: str = Field(description="ID заказа")
        debug_data: dict[str, Any] = Field(default_factory=dict, description="Отладочные данные")

═══════════════════════════════════════════════════════════════════════════════
PYDANTIC BASEMODEL
═══════════════════════════════════════════════════════════════════════════════

Наследование от pydantic BaseModel даёт:

- Валидация типов при создании экземпляра.
- Описание полей через ``Field(description="...")``.
- Ограничения через ``Field(gt=0, min_length=3, pattern=...)``.
- JSON Schema через ``model_json_schema()`` — для OpenAPI и MCP.
- Сериализация через ``model_dump()`` — для FastAPI и MCP адаптеров.

═══════════════════════════════════════════════════════════════════════════════
СОВМЕСТИМОСТЬ С МИКСИНАМИ
═══════════════════════════════════════════════════════════════════════════════

ReadableMixin обеспечивает dict-подобный доступ на чтение:

    result["order_id"]           # → "ORD-1"
    result.get("status")         # → "created"
    result.resolve("total")      # → 1500.0
    result.keys()                # → ["order_id", "status", "total"]

DescribedFieldsGateHost — маркерный миксин, обязывающий каждое поле
иметь ``Field(description="...")``. MetadataBuilder проверяет это
при сборке метаданных.

═══════════════════════════════════════════════════════════════════════════════
ОТЛИЧИЕ ОТ BaseParams И BaseState
═══════════════════════════════════════════════════════════════════════════════

    BaseParams  — pydantic BaseModel, frozen=True. Входные параметры.
    BaseResult  — pydantic BaseModel, frozen=True. Результат действия.
    BaseState   — обычный класс (не pydantic), frozen. Промежуточное
                  состояние конвейера с динамическими полями.

Все три типа — read-only после создания. Единственный способ «изменить»
любой из них — создать новый экземпляр.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В КОНВЕЙЕРЕ
═══════════════════════════════════════════════════════════════════════════════

Summary-аспект создаёт Result:

    @summary_aspect("Формирование результата")
    async def build_result_summary(self, params, state, box, connections):
        return OrderResult(
            order_id=f"ORD_{params.user_id}",
            status="created",
            total=state["total"],
        )

Обработчик @on_error создаёт альтернативный Result:

    @on_error(ValueError, description="Ошибка валидации")
    async def validation_on_error(self, params, state, box, connections, error):
        return OrderResult(order_id="ERR", status="validation_error", total=0)

Плагины читают Result через event.result, но не могут его изменить.
Адаптеры (FastAPI, MCP) сериализуют через model_dump().

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field
    from action_machine.core.base_result import BaseResult

    class OrderResult(BaseResult):
        order_id: str = Field(description="ID созданного заказа")
        status: str = Field(description="Статус заказа")
        total: float = Field(description="Итоговая сумма", ge=0)

    result = OrderResult(order_id="ORD-123", status="created", total=1500.0)

    # Чтение через ReadableMixin:
    result["status"]            # → "created"
    result.resolve("total")     # → 1500.0
    result.keys()               # → ["order_id", "status", "total"]

    # Запись запрещена (frozen):
    result.status = "paid"      # → ValidationError
    result["status"] = "paid"   # → TypeError

    # «Изменение» — создание нового экземпляра:
    updated = result.model_copy(update={"status": "paid"})

    # JSON Schema для FastAPI и MCP:
    OrderResult.model_json_schema()
    # {"properties": {"order_id": {"description": "ID созданного заказа", ...}, ...}}
"""

from pydantic import BaseModel, ConfigDict

from action_machine.core.described_fields_gate_host import DescribedFieldsGateHost
from action_machine.core.readable_mixin import ReadableMixin


class BaseResult(BaseModel, ReadableMixin, DescribedFieldsGateHost):
    """
    Frozen-результат действия (pydantic-based).

    Наследуйте этот класс для создания конкретных результатов.
    Каждое поле описывается через pydantic ``Field(description="...")``.
    Описание обязательно — MetadataBuilder проверяет при сборке.

    Результат неизменяем после создания (frozen=True). Все поля должны быть
    объявлены в классе-наследнике — произвольные поля запрещены (extra="forbid").

    Пример:
        class OrderResult(BaseResult):
            order_id: str = Field(description="ID заказа")
            total: float = Field(description="Итого", ge=0)
            status: str = Field(description="Статус", examples=["created"])
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
