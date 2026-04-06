# src/action_machine/core/described_fields_gate_host.py
"""
Модуль: DescribedFieldsGateHost — маркерный миксин, обозначающий
обязательность описания полей через pydantic Field(description="...").

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

DescribedFieldsGateHost — миксин-маркер, который обозначает, что все поля
класса (pydantic-модели) обязаны иметь непустое описание через
``Field(description="...")``. Наследуется BaseParams и BaseResult.

MetadataBuilder при сборке метаданных проверяет: если класс наследует
DescribedFieldsGateHost и содержит pydantic-поля — каждое поле обязано
иметь непустой description. Если хотя бы одно поле без описания —
TypeError с указанием класса и поля.

Проверка выполняется только для классов с собственными полями. Базовые
классы BaseParams и BaseResult без полей не проверяются. Пустые классы
(MockParams, MockResult в тестах) тоже не проверяются — у них нет полей.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class BaseParams(BaseSchema, DescribedFieldsGateHost):
        model_config = ConfigDict(frozen=True, extra="forbid")

    class BaseResult(BaseSchema, DescribedFieldsGateHost):
        model_config = ConfigDict(frozen=True, extra="forbid")

    class OrderParams(BaseParams):
        user_id: str = Field(description="ID пользователя")    ← OK
        amount: float = Field(description="Сумма заказа")       ← OK

    class BadParams(BaseParams):
        user_id: str                                             ← нет Field()
        amount: float = Field()                                  ← нет description

    # MetadataBuilder.build(Action с BadParams) → TypeError:
    # "Поле 'user_id' в BadParams не имеет описания.
    #  Используйте Field(description=\"...\")."

BaseParams и BaseResult наследуют BaseSchema [2], которая предоставляет
dict-подобный доступ к полям и dot-path навигацию через resolve().

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

1. МАРКЕР БЕЗ ЛОГИКИ. Миксин не содержит полей, методов или логики.
   Его единственная функция — служить проверочным маркером для
   issubclass() в валидаторах MetadataBuilder.

2. ОБЯЗАТЕЛЬНОСТЬ. Наличие гейт-хоста в MRO класса означает, что
   каждое поле обязано иметь описание. Это безусловный инвариант.

3. ЕДИНООБРАЗИЕ. Следует тому же паттерну, что и все остальные
   гейт-миксины системы (RoleGateHost, ActionMetaGateHost,
   AspectGateHost и др.).

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from pydantic import Field
    from action_machine.core.base_params import BaseParams

    # Корректно — все поля имеют описание:
    class OrderParams(BaseParams):
        user_id: str = Field(description="ID пользователя")
        amount: float = Field(description="Сумма заказа", gt=0)

    # Ошибка — поле без описания:
    class BadParams(BaseParams):
        user_id: str  # → TypeError при сборке метаданных
"""


class DescribedFieldsGateHost:
    """
    Маркерный миксин, обозначающий обязательность описания полей
    через pydantic Field(description="...").

    Наследуется BaseParams и BaseResult. Класс, наследующий
    DescribedFieldsGateHost и содержащий pydantic-поля, обязан
    иметь непустое description для каждого поля. MetadataBuilder
    проверяет это при сборке ClassMetadata.

    Миксин не содержит логики, полей или методов.
    """

    pass
