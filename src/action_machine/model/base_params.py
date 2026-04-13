# src/action_machine/model/base_params.py
"""
BaseParams — иммутабельные параметры действия.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

BaseParams — базовый класс для всех parameters действий в системе
ActionMachine. Определяет структуру входных данных, которые передаются
в конвейер аспектов при выполнении действия (Action).

Параметры задаются один раз при создании и не могут быть изменены
в процессе обработки — это гарантируется настройкой frozen=True.
Произвольные поля запрещены (extra="forbid") — только явно объявленные
в классе-наследнике.

═══════════════════════════════════════════════════════════════════════════════
ИЕРАРХИЯ
═══════════════════════════════════════════════════════════════════════════════

    BaseSchema(BaseModel)
        └── BaseParams (frozen=True, extra="forbid")

═══════════════════════════════════════════════════════════════════════════════
ИММУТАБЕЛЬНОСТЬ
═══════════════════════════════════════════════════════════════════════════════

Иммутабельность parameters — архитектурное решение, обеспечивающее:

- Предсказуемость: аспекты не могут случайно изменить входные данные.
- Безопасность: один и тот же объект Params безопасно передаётся
  во все аспекты, плагины и обработчики ошибок.
- Отладку: параметры на любом этапе конвейера всегда совпадают
  с тем, что было передано на входе.

═══════════════════════════════════════════════════════════════════════════════
СТРОГАЯ СТРУКТУРА (extra="forbid")
═══════════════════════════════════════════════════════════════════════════════

Параметры содержат ровно те поля, которые объявлены в конкретном
наследнике. Передача неизвестного поля при создании вызывает
ValidationError. Это защита от опечаток и случайных данных.

Если нужны дополнительные поля — создаётся наследник с явным
объявлением:

    class ExtendedOrderParams(OrderParams):
        priority: int = Field(description="Приоритет заказа")

═══════════════════════════════════════════════════════════════════════════════
ОПИСАНИЕ ПОЛЕЙ
═══════════════════════════════════════════════════════════════════════════════

Каждое поле описывается через pydantic Field(description="...").
Описание обязательно — при сборке метаданных вызывайте
``validate_described_schema`` / ``validate_described_schemas_for_action``
(см. ``described_fields_intent``). Описания используются для генерации
OpenAPI-документации (FastAPI), JSON Schema (MCP) и интроспекции.

═══════════════════════════════════════════════════════════════════════════════
PYDANTIC ВОЗМОЖНОСТИ
═══════════════════════════════════════════════════════════════════════════════

Наследование от pydantic BaseModel (через BaseSchema) даёт:

- Validation типов при создании экземпляра.
- Ограничения через Field(gt=0, min_length=3, pattern=...).
- Примеры через Field(examples=["user_123"]).
- JSON Schema через model_json_schema() — для OpenAPI и MCP.
- Сериализация через model_dump() — для адаптеров и логов.

═══════════════════════════════════════════════════════════════════════════════
DICT-ПОДОБНЫЙ ДОСТУП (унаследован от BaseSchema)
═══════════════════════════════════════════════════════════════════════════════

    params["user_id"]                    # → "user_123"
    "amount" in params                   # → True
    params.get("currency", "RUB")        # → "RUB"
    list(params.keys())                  # → ["user_id", "amount", "currency"]
    params.resolve("address.city")       # → "Moscow"
    params.model_dump()                  # → {"user_id": "user_123", ...}

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field
    from action_machine.model.base_params import BaseParams

    class OrderParams(BaseParams):
        user_id: str = Field(description="ID пользователя", examples=["user_123"])
        amount: float = Field(description="Сумма заказа в рублях", gt=0)
        currency: str = Field(default="RUB", description="Код валюты ISO 4217")

    params = OrderParams(user_id="user_123", amount=1500.0)

    params["user_id"]           # → "user_123"
    params.resolve("currency")  # → "RUB"
    params.keys()               # → ["user_id", "amount", "currency"]

    # Запись запрещена (frozen):
    params.amount = 0           # → ValidationError

    # Лишние поля запрещены (forbid):
    OrderParams(user_id="x", amount=1, unknown="y")  # → ValidationError

    # JSON Schema для FastAPI и MCP:
    OrderParams.model_json_schema()
    # {"properties": {"user_id": {"description": "ID пользователя", ...}, ...}}
"""

from pydantic import ConfigDict

from action_machine.intents.described_fields.marker import DescribedFieldsIntent
from action_machine.model.base_schema import BaseSchema


class BaseParams(BaseSchema, DescribedFieldsIntent):
    """
    Иммутабельные параметры действия (frozen, forbid).

    Наследует dict-подобный доступ и dot-path навигацию от BaseSchema.
    Наследует контроль обязательности описаний полей от DescribedFieldsIntent.

    Запись в поля запрещена на уровне pydantic (frozen=True).
    Произвольные поля запрещены (extra="forbid").

    Конкретные параметры создаются наследованием:

        class CreateUserParams(BaseParams):
            username: str = Field(description="Имя пользователя", min_length=3)
            email: str = Field(description="Email адрес")
            role: str = Field(default="user", description="Роль пользователя")
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
