# src/action_machine/core/base_result.py
"""
Базовый класс для результата выполнения действия.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseResult — базовый класс для всех результатов действий в системе
ActionMachine. Наследует pydantic BaseModel для валидации типов,
описания полей и генерации JSON Schema.

В отличие от BaseParams, результат НЕ заморожен — поля могут быть
изменены после создания. Это необходимо, потому что результат
формируется поэтапно: summary-аспект создаёт базовый результат,
а плагины или внешний код могут дополнять его.

Поддерживает динамические поля через extra="allow" — можно записывать
произвольные ключи через dict-подобный интерфейс WritableMixin.

═══════════════════════════════════════════════════════════════════════════════
PYDANTIC КОНФИГУРАЦИЯ
═══════════════════════════════════════════════════════════════════════════════

    extra="allow" — разрешает запись полей, не объявленных в классе.
        result["debug_info"] = "something" — не вызовет ошибку,
        даже если поле debug_info не объявлено в модели.

    arbitrary_types_allowed=True — разрешает нестандартные типы
        в полях (например, кастомные объекты).

    Без frozen — запись через setattr и WritableMixin работает.

═══════════════════════════════════════════════════════════════════════════════
СОВМЕСТИМОСТЬ С МИКСИНАМИ
═══════════════════════════════════════════════════════════════════════════════

ReadableMixin — dict-подобный доступ на чтение: result["key"],
result.get("key"), result.keys(), result.resolve("nested.key").

WritableMixin — dict-подобный доступ на запись: result["key"] = value,
del result["key"], result.write("key", value, allowed_keys=[...]),
result.update({"a": 1, "b": 2}).

Оба миксина работают через getattr/setattr/delattr — совместимы
с pydantic BaseModel без изменений.

═══════════════════════════════════════════════════════════════════════════════
ОТЛИЧИЕ ОТ BaseParams И BaseState
═══════════════════════════════════════════════════════════════════════════════

    BaseParams  — pydantic BaseModel, frozen=True, только чтение.
    BaseResult  — pydantic BaseModel, mutable, чтение и запись.
    BaseState   — dataclass, mutable, динамические поля. НЕ pydantic.

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

    # Запись через WritableMixin:
    result["status"] = "paid"
    result["debug_info"] = "extra data"  # динамическое поле (extra="allow")

    # JSON Schema для FastAPI:
    OrderResult.model_json_schema()
"""

from pydantic import BaseModel, ConfigDict

from action_machine.core.described_fields_gate_host import DescribedFieldsGateHost
from action_machine.core.readable_mixin import ReadableMixin
from action_machine.core.writable_mixin import WritableMixin


class BaseResult(BaseModel, ReadableMixin, WritableMixin, DescribedFieldsGateHost):
    """
    Результат действия (mutable, pydantic-based).

    Наследуйте этот класс для создания конкретных результатов.
    Каждое поле описывается через pydantic Field(description="...").
    Описание обязательно — MetadataBuilder проверяет при сборке.

    Результат может быть изменяемым — плагины и аспекты могут
    дополнять его новыми полями через dict-подобный интерфейс.
    Динамические поля разрешены через extra="allow".

    Пример:
        class OrderResult(BaseResult):
            order_id: str = Field(description="ID заказа")
            total: float = Field(description="Итого", ge=0)
            status: str = Field(description="Статус", examples=["created"])
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="allow",
    )
