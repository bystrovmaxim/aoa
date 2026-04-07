"""
Пакет доменов и модели предметной области ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит декларативную модель предметной области. Модель описывает
сущности, их поля, связи между ними и жизненные циклы — и больше ничего.
Она не знает про базы данных, HTTP, файлы или любой другой внешний мир.
Это чистое ядро в терминах гексагональной архитектуры.

═══════════════════════════════════════════════════════════════════════════════
КООРДИНАТОР
═══════════════════════════════════════════════════════════════════════════════

Единый координатор системы — GateCoordinator из core/. Сущности
регистрируются в том же графе rustworkx, что и Action, Plugin,
ResourceManager — один граф на всю систему. Информация о сущностях
хранится в payload узлов графа, как и для Action.

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

Домены:
    BaseDomain — абстрактный базовый класс для всех доменов.

Сущности:
    BaseEntity — абстрактный базовый класс для всех сущностей.
    EntityGateHost — маркерный миксин, разрешающий @entity.
    entity — декоратор уровня класса для объявления сущности.

Конечные автоматы:
    Lifecycle — декларативный конечный автомат жизненного цикла.
    StateType — enum классификации состояний: INITIAL, INTERMEDIATE, FINAL.
    StateInfo — frozen dataclass метаданных одного состояния.

Связи между сущностями:
    CompositeOne[T], CompositeMany[T]     — Composition
    AggregateOne[T], AggregateMany[T]     — Aggregation
    AssociationOne[T], AssociationMany[T]  — Association
    RelationType — enum типа владения.
    Inverse, NoInverse, Rel — маркеры связей.

Утилиты:
    build — сборка сущностей из плоских данных.
    make — тестовая фабрика с автогенерацией дефолтов.

Исключения:
    FieldNotLoadedError, RelationNotLoadedError,
    EntityDecoratorError, LifecycleValidationError.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.domain import (
        BaseDomain, BaseEntity, entity,
        Lifecycle, StateType,
        AssociationOne, CompositeMany,
        Inverse, Rel, build, make,
    )
    from action_machine.core.gate_coordinator import GateCoordinator

    class ShopDomain(BaseDomain):
        name = "shop"
        description = "Интернет-магазин"

    @entity(description="Заказ клиента", domain=ShopDomain)
    class OrderEntity(BaseEntity):
        lifecycle = (
            Lifecycle("Жизненный цикл заказа")
            .state("new", "Новый").to("confirmed", "cancelled").initial()
            .state("confirmed", "Подтверждён").to("shipped").intermediate()
            .state("delivered", "Доставлен").final()
            .state("cancelled", "Отменён").final()
        )
        id: str = Field(description="ID заказа")
        amount: float = Field(description="Сумма", ge=0)

    coordinator = GateCoordinator()
    coordinator.register_entity(OrderEntity)
    order = build({"id": "123", "amount": 100.0}, OrderEntity)
"""

from .base_domain import BaseDomain
from .entity import BaseEntity
from .entity_decorator import entity
from .entity_gate_host import EntityGateHost
from .exceptions import (
    EntityDecoratorError,
    FieldNotLoadedError,
    LifecycleValidationError,
    RelationNotLoadedError,
)
from .hydration import build
from .lifecycle import Lifecycle, StateInfo, StateType
from .relation_containers import (
    AggregateMany,
    AggregateOne,
    AssociationMany,
    AssociationOne,
    BaseRelationMany,
    BaseRelationOne,
    CompositeMany,
    CompositeOne,
    RelationType,
)
from .relation_markers import Inverse, NoInverse, Rel
from .testing import make

__all__ = [
    # Домены
    "BaseDomain",
    # Сущности
    "BaseEntity",
    "EntityGateHost",
    "entity",
    # Конечные автоматы
    "Lifecycle",
    "StateType",
    "StateInfo",
    # Контейнеры связей
    "BaseRelationOne",
    "BaseRelationMany",
    "CompositeOne",
    "CompositeMany",
    "AggregateOne",
    "AggregateMany",
    "AssociationOne",
    "AssociationMany",
    "RelationType",
    # Маркеры связей
    "Inverse",
    "NoInverse",
    "Rel",
    # Утилиты
    "build",
    "make",
    # Исключения
    "EntityDecoratorError",
    "FieldNotLoadedError",
    "LifecycleValidationError",
    "RelationNotLoadedError",
]
