# src/action_machine/core/base_params.py
"""
Базовый класс для параметров действия.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseParams — базовый класс для всех параметров действий в системе
ActionMachine. Наследует pydantic BaseModel для валидации типов,
описания полей и генерации JSON Schema.

Параметры действия являются неизменяемыми (frozen=True) после создания.
Это предотвращает случайное изменение входных данных аспектами или
плагинами в ходе выполнения конвейера.

Наследует ReadableMixin для dict-подобного доступа к полям и навигации
по вложенным объектам через метод resolve(). Наследует
DescribedFieldsGateHost для контроля обязательности описаний полей.

═══════════════════════════════════════════════════════════════════════════════
PYDANTIC BASEMODEL
═══════════════════════════════════════════════════════════════════════════════

Переход с dataclass на pydantic BaseModel даёт:

1. ВАЛИДАЦИЯ ТИПОВ — pydantic проверяет типы при создании экземпляра.
   Передача строки в поле int вызовет ValidationError.

2. ОПИСАНИЕ ПОЛЕЙ — каждое поле описывается через Field(description="...").
   MetadataBuilder проверяет обязательность описаний при сборке метаданных.

3. ОГРАНИЧЕНИЯ — Field поддерживает gt, ge, lt, le, min_length,
   max_length, pattern, examples и другие constraints из коробки.

4. JSON SCHEMA — model_json_schema() генерирует JSON Schema
   с descriptions, constraints, examples. FastAPI использует это
   для автоматической генерации OpenAPI документации.

5. FASTAPI СОВМЕСТИМОСТЬ — pydantic BaseModel является нативным типом
   для FastAPI. Модели передаются в эндпоинты напрямую, без адаптеров.

═══════════════════════════════════════════════════════════════════════════════
СОВМЕСТИМОСТЬ С МИКСИНАМИ
═══════════════════════════════════════════════════════════════════════════════

ReadableMixin работает через getattr/hasattr/vars(). Pydantic BaseModel
хранит данные полей в атрибутах экземпляра. Все методы ReadableMixin
(keys, values, items, resolve, __getitem__, __contains__, get)
совместимы без изменений.

DescribedFieldsGateHost — маркерный миксин без логики. Совместим
с любым классом.

═══════════════════════════════════════════════════════════════════════════════
ОТЛИЧИЕ ОТ BaseResult И BaseState
═══════════════════════════════════════════════════════════════════════════════

    BaseParams  — pydantic BaseModel, frozen=True, только чтение.
    BaseResult  — pydantic BaseModel, mutable, чтение и запись.
    BaseState   — dataclass, mutable, динамические поля. НЕ pydantic.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field
    from action_machine.core.base_params import BaseParams

    class OrderParams(BaseParams):
        user_id: str = Field(description="ID пользователя", examples=["user_123"])
        amount: float = Field(description="Сумма заказа в рублях", gt=0)
        currency: str = Field(default="RUB", description="Код валюты ISO 4217")

    params = OrderParams(user_id="user_123", amount=1500.0)

    # Dict-подобный доступ через ReadableMixin:
    params["user_id"]           # → "user_123"
    params.resolve("currency")  # → "RUB"
    params.keys()               # → ["user_id", "amount", "currency"]

    # Frozen — нельзя изменить:
    params.amount = 0           # → ValidationError

    # JSON Schema для FastAPI:
    OrderParams.model_json_schema()
    # {"properties": {"user_id": {"description": "ID пользователя", ...}, ...}}
"""

from pydantic import BaseModel, ConfigDict

from action_machine.core.described_fields_gate_host import DescribedFieldsGateHost
from action_machine.core.readable_mixin import ReadableMixin


class BaseParams(BaseModel, ReadableMixin, DescribedFieldsGateHost):
    """
    Параметры действия (read-only, pydantic-based).

    Наследуйте этот класс для создания конкретных параметров.
    Каждое поле описывается через pydantic Field(description="...").
    Описание обязательно — MetadataBuilder проверяет при сборке.

    Параметры передаются в конвейер аспектов и доступны на всех этапах.
    Аспекты читают параметры, но не могут их изменять (frozen=True).

    Пример:
        class CreateUserParams(BaseParams):
            username: str = Field(description="Имя пользователя", min_length=3)
            email: str = Field(description="Email адрес")
            role: str = Field(default="user", description="Роль пользователя")
    """

    model_config = ConfigDict(frozen=True)
