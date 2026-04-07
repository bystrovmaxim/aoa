# tests/domain/entities.py
"""
Тестовые сущности доменной модели.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Определяет тестовые сущности для проверки функционала домена:
BaseEntity, @entity декоратор, Lifecycle, связи, GateCoordinator.

═══════════════════════════════════════════════════════════════════════════════
СУЩНОСТИ
═══════════════════════════════════════════════════════════════════════════════

- SampleEntity — простая сущность без связей и lifecycle.
- LifecycleEntity — сущность с жизненным циклом (DraftLifecycle).
- RelatedEntity — сущность со связями.
- ComplexEntity — сущность со всем функционалом.

═══════════════════════════════════════════════════════════════════════════════
СПЕЦИАЛИЗИРОВАННЫЕ КЛАССЫ LIFECYCLE
═══════════════════════════════════════════════════════════════════════════════

DraftLifecycle — автомат с тремя состояниями: draft → active → archived.
Используется в LifecycleEntity и ComplexEntity.

_template определяется при определении класса (import-time).
GateCoordinator при старте находит DraftLifecycle в model_fields,
читает _template и проверяет 8 правил целостности.

Каждый экземпляр сущности хранит своё текущее состояние:
    entity.lifecycle.current_state       → "draft"
    entity.lifecycle.can_transition("active")  → True
    entity.lifecycle.available_transitions     → {"active"}

Переход состояния (frozen-сущность):
    new_lc = entity.lifecycle.transition("active")
    updated = entity.model_copy(update={"lifecycle": new_lc})

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

Тестовые сущности используются в unit-тестах для проверки:

- Корректности создания через @entity
- Сборки метаданных через GateCoordinator.get()
- Валидации Lifecycle (8 правил целостности)
- Правильности связей (Annotated + Inverse/NoInverse + Rel)
- Функционирования build() и make()
- Специализированных классов Lifecycle (current_state, transition)
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from action_machine.domain import (
    AggregateMany,
    AssociationOne,
    BaseEntity,
    Lifecycle,
    NoInverse,
    Rel,
    entity,
)
from action_machine.domain.base_domain import BaseDomain

# ═══════════════════════════════════════════════════════════════════════════════
# ДОМЕН
# ═══════════════════════════════════════════════════════════════════════════════


class TestDomain(BaseDomain):
    """Тестовый домен для проверки функционала."""

    name = "test"
    description = "Тестовый домен"


# ═══════════════════════════════════════════════════════════════════════════════
# СПЕЦИАЛИЗИРОВАННЫЕ КЛАССЫ LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════════


class DraftLifecycle(Lifecycle):
    """
    Автомат с тремя состояниями: draft → active → archived.

    _template создаётся при import-time. GateCoordinator проверяет
    8 правил целостности при старте приложения.
    """

    _template = (
        Lifecycle()
        .state("draft", "Черновик").to("active").initial()
        .state("active", "Активный").to("archived").intermediate()
        .state("archived", "Архивирован").final()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# СУЩНОСТИ
# ═══════════════════════════════════════════════════════════════════════════════


@entity(description="Простая тестовая сущность", domain=TestDomain)
class SampleEntity(BaseEntity):
    """Простая сущность для базовых тестов. Без связей и Lifecycle."""

    id: str = Field(description="Идентификатор")
    name: str = Field(description="Название")
    value: int = Field(description="Значение", ge=0)


@entity(description="Сущность с жизненным циклом", domain=TestDomain)
class LifecycleEntity(BaseEntity):
    """
    Сущность для тестирования Lifecycle.

    lifecycle — обычное pydantic-поле (DraftLifecycle | None).
    Каждый экземпляр хранит своё текущее состояние:

        entity = LifecycleEntity(id="1", lifecycle=DraftLifecycle("draft"))
        entity.lifecycle.current_state  # → "draft"

    Без lifecycle:
        entity = LifecycleEntity(id="1", lifecycle=None)
        entity.lifecycle  # → None

    Частичная загрузка:
        entity = LifecycleEntity.partial(id="1")
        entity.lifecycle  # → FieldNotLoadedError
    """

    id: str = Field(description="Идентификатор")
    lifecycle: DraftLifecycle | None = Field(description="Жизненный цикл")


@entity(description="Связанная сущность", domain=TestDomain)
class RelatedEntity(BaseEntity):
    """
    Сущность для тестирования связей.

    parent — ассоциация на саму себя (Optional, без Inverse).
    children — агрегация коллекции на саму себя (без Inverse).
    """

    id: str = Field(description="Идентификатор")
    title: str = Field(description="Заголовок")

    parent: Annotated[
        AssociationOne[RelatedEntity] | None,
        NoInverse(),
    ] = Rel(description="Родительская сущность")

    children: Annotated[
        AggregateMany[RelatedEntity] | None,
        NoInverse(),
    ] = Rel(description="Дочерние сущности")


@entity(description="Комплексная сущность", domain=TestDomain)
class ComplexEntity(BaseEntity):
    """
    Сущность со всем функционалом для комплексных тестов.

    Содержит:
    - Простые поля (id, name, amount).
    - Lifecycle (DraftLifecycle).
    - Связь AssociationOne на LifecycleEntity (без Inverse).
    - Связь AggregateMany на RelatedEntity (без Inverse).
    """

    id: str = Field(description="Идентификатор")
    name: str = Field(description="Название")
    amount: float = Field(description="Сумма", ge=0)

    lifecycle: DraftLifecycle | None = Field(description="Жизненный цикл")

    owner: Annotated[
        AssociationOne[LifecycleEntity] | None,
        NoInverse(),
    ] = Rel(description="Владелец")

    related_items: Annotated[
        AggregateMany[RelatedEntity] | None,
        NoInverse(),
    ] = Rel(description="Связанные элементы")
