# src/action_machine/domain/relation_containers.py
"""
Контейнеры связей доменной модели ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит шесть generic-контейнеров для объявления связей между
сущностями доменной модели. Контейнеры различаются по двум осям:

1. ТИП ВЛАДЕНИЯ (три типа из ArchiMate):
   - Composition — сильное владение. При удалении родителя дочерние
     объекты удаляются. Ребёнок не может существовать без родителя.
     Пример: Заказ → Позиции заказа.
   - Aggregation — слабое владение. При удалении родителя дочерние
     объекты отвязываются, но продолжают существовать.
     Пример: Команда → Сотрудники.
   - Association — равноправная связь без владения. Удаление одной
     стороны не затрагивает другую.
     Пример: Заказ ↔ Клиент.

2. КАРДИНАЛЬНОСТЬ (два варианта):
   - One — ссылка на одну сущность.
   - Many — ссылка на коллекцию сущностей.

Итого шесть контейнеров:
    CompositeOne[T]     — один дочерний объект (composition)
    CompositeMany[T]    — коллекция дочерних объектов (composition)
    AggregateOne[T]     — один агрегированный объект
    AggregateMany[T]    — коллекция агрегированных объектов
    AssociationOne[T]   — одна ассоциированная сущность
    AssociationMany[T]  — коллекция ассоциированных сущностей

═══════════════════════════════════════════════════════════════════════════════
КОНТЕЙНЕР СВЯЗИ: id ВСЕГДА, ОБЪЕКТ — ОПЦИОНАЛЬНО
═══════════════════════════════════════════════════════════════════════════════

Контейнеры One (CompositeOne, AggregateOne, AssociationOne) хранят:
- id : Any — идентификатор связанной сущности. Всегда присутствует.
- entity : T | None — полный загруженный объект. Может быть None,
  если менеджер загрузил только id.

Контейнеры Many (CompositeMany, AggregateMany, AssociationMany) хранят:
- ids : tuple[Any, ...] — кортеж идентификаторов связанных сущностей.
- entities : tuple[T, ...] — кортеж загруженных объектов. Может быть
  пустым, если менеджер загрузил только идентификаторы.

Тип id не фиксирован — это обычное поле целевой сущности, определяемое
разработчиком. Модель не навязывает формат идентификатора: str, int,
UUID — любой тип. У сущности может не быть поля id вообще.

═══════════════════════════════════════════════════════════════════════════════
ПРОКСИРОВАНИЕ АТРИБУТОВ (КОНТЕЙНЕРЫ ONE)
═══════════════════════════════════════════════════════════════════════════════

Контейнеры One поддерживают проксирование атрибутов на загруженную
сущность через __getattr__:

    order.customer.name    # → проксируется на entity.name

Если entity загружен (не None) — атрибут читается с entity.
Если entity не загружен (None) — RelationNotLoadedError с информативным
сообщением.

Доступ к id всегда работает, независимо от загрузки entity:

    order.customer.id      # → всегда работает (id хранится в контейнере)
    order.customer.name    # → работает только если entity загружен

═══════════════════════════════════════════════════════════════════════════════
FROZEN-СЕМАНТИКА
═══════════════════════════════════════════════════════════════════════════════

Все контейнеры неизменяемы после создания. Запись и удаление атрибутов
запрещены через __setattr__ и __delattr__. Это согласуется с frozen-
семантикой BaseEntity: данные сущности фиксируются при загрузке и
не меняются в ходе обработки.

═══════════════════════════════════════════════════════════════════════════════
МАТРИЦА СОВМЕСТИМОСТИ ТИПОВ ВЛАДЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

При двусторонней связи (Inverse) типы владения обеих сторон должны быть
совместимы. Координатор проверяет по матрице:

    Composite  ↔ Association    — допустимо (родитель → дочерний → обратная ссылка)
    Aggregate  ↔ Association    — допустимо
    Association ↔ Association   — допустимо (равноправная связь)
    Composite  ↔ Composite      — запрещено (два владельца)
    Composite  ↔ Aggregate      — запрещено (конфликт семантики владения)
    Aggregate  ↔ Aggregate      — запрещено (два владельца)

Обратная сторона Composite/Aggregate-связи должна быть Association.

═══════════════════════════════════════════════════════════════════════════════
ENUM ТИПОВ ВЛАДЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

RelationType — enum, классифицирующий тип владения контейнера.
Используется координатором для проверки матрицы совместимости
и построения ArchiMate-диаграмм.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from typing import Annotated
    from pydantic import Field
    from action_machine.domain import (
        BaseEntity, entity, BaseDomain, Lifecycle,
        AssociationOne, AssociationMany, CompositeMany,
        Inverse, NoInverse, Rel,
    )

    class ShopDomain(BaseDomain):
        name = "shop"
        description = "Интернет-магазин"

    @entity(description="Клиент", domain=ShopDomain)
    class CustomerEntity(BaseEntity):
        id: str = Field(description="ID клиента")
        name: str = Field(description="Имя клиента")

        orders: Annotated[
            AssociationMany[OrderEntity],
            Inverse(OrderEntity, "customer"),
        ] = Rel(description="Заказы клиента")

    @entity(description="Заказ", domain=ShopDomain)
    class OrderEntity(BaseEntity):
        id: str = Field(description="ID заказа")
        amount: float = Field(description="Сумма", ge=0)

        customer: Annotated[
            AssociationOne[CustomerEntity],
            Inverse(CustomerEntity, "orders"),
        ] = Rel(description="Клиент, оформивший заказ")

        items: Annotated[
            CompositeMany[OrderItemEntity],
            Inverse(OrderItemEntity, "order"),
        ] = Rel(description="Позиции заказа")

    # Создание контейнера One (менеджером):
    customer_ref = AssociationOne(id="CUST-001", entity=customer_obj)
    customer_ref.id        # → "CUST-001"
    customer_ref.name      # → проксируется на customer_obj.name

    # Создание контейнера One (только id):
    customer_ref = AssociationOne(id="CUST-001")
    customer_ref.id        # → "CUST-001"
    customer_ref.name      # → RelationNotLoadedError

    # Создание контейнера Many (менеджером):
    items_ref = CompositeMany(ids=("ITEM-1", "ITEM-2"), entities=(item1, item2))
    items_ref.ids           # → ("ITEM-1", "ITEM-2")
    items_ref.entities      # → (item1, item2)
    len(items_ref)          # → 2
    items_ref[0]            # → item1
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Generic, TypeVar, overload

from action_machine.domain.exceptions import RelationNotLoadedError

T = TypeVar("T")


class RelationType(Enum):
    """
    Тип владения связи между сущностями.

    Соответствует трём структурным отношениям ArchiMate:

    COMPOSITION — сильное владение. Дочерний объект не существует без
                  родителя. При удалении родителя дочерние удаляются.
                  ArchiMate: Composition relationship.

    AGGREGATION — слабое владение. Дочерний объект может существовать
                  самостоятельно. При удалении родителя дочерние
                  отвязываются.
                  ArchiMate: Aggregation relationship.

    ASSOCIATION — равноправная связь без владения. Удаление одной
                  стороны не затрагивает другую.
                  ArchiMate: Association relationship.
    """

    COMPOSITION = "composition"
    AGGREGATION = "aggregation"
    ASSOCIATION = "association"


# ═════════════════════════════════════════════════════════════════════════════
# Базовые классы контейнеров
# ═════════════════════════════════════════════════════════════════════════════


class BaseRelationOne(Generic[T]):
    """
    Базовый контейнер связи «к одному» (One).

    Хранит идентификатор связанной сущности (id) и опционально загруженный
    объект (entity). Поддерживает проксирование атрибутов на entity:
    обращение к атрибуту контейнера, не являющемуся id или entity,
    делегируется в entity если он загружен.

    Frozen после создания. Запись и удаление атрибутов запрещены.

    Подклассы (CompositeOne, AggregateOne, AssociationOne) отличаются
    только значением класс-атрибута relation_type, определяющего
    семантику владения.

    Атрибуты:
        id : Any
            Идентификатор связанной сущности. Всегда присутствует.
            Тип определяется разработчиком (str, int, UUID и т.д.).

        entity : T | None
            Загруженный объект связанной сущности. None если менеджер
            загрузил только id. Проксирование атрибутов работает
            только при entity is not None.

        relation_type : RelationType
            Тип владения. Определяется в подклассах. Используется
            координатором для проверки матрицы совместимости.
    """

    __slots__ = ("_entity", "_id")

    relation_type: RelationType  # Определяется в подклассах

    def __init__(self, *, id: Any, entity: T | None = None) -> None:
        """
        Инициализирует контейнер связи «к одному».

        Аргументы:
            id: идентификатор связанной сущности. Обязательный.
            entity: загруженный объект сущности. Опциональный.
                    None означает: менеджер загрузил только id.

        Исключения:
            ValueError: если id is None.
        """
        if id is None:
            raise ValueError(
                f"{self.__class__.__name__}: id не может быть None. "
                f"Контейнер связи обязан хранить идентификатор."
            )
        object.__setattr__(self, "_id", id)
        object.__setattr__(self, "_entity", entity)

    @property
    def id(self) -> Any:
        """Идентификатор связанной сущности. Всегда доступен."""
        return self._id

    @property
    def entity(self) -> T | None:
        """Загруженный объект или None."""
        return self._entity

    @property
    def is_loaded(self) -> bool:
        """True если объект сущности загружен (entity is not None)."""
        return self._entity is not None

    def __getattr__(self, name: str) -> Any:
        """
        Проксирует доступ к атрибутам на загруженную сущность.

        Вызывается Python только для атрибутов, НЕ найденных через
        стандартный __getattribute__ (т.е. не id, entity, is_loaded,
        relation_type и не приватные атрибуты __slots__).

        Если entity загружен — делегирует getattr(entity, name).
        Если entity не загружен — RelationNotLoadedError.

        Аргументы:
            name: имя запрашиваемого атрибута.

        Возвращает:
            Значение атрибута entity.

        Исключения:
            RelationNotLoadedError: если entity is None.
            AttributeError: если entity загружен, но не имеет атрибута.
        """
        entity = object.__getattribute__(self, "_entity")
        if entity is None:
            entity_id = object.__getattribute__(self, "_id")
            raise RelationNotLoadedError(
                container_class_name=self.__class__.__name__,
                attribute_name=name,
                entity_id=entity_id,
            )
        return getattr(entity, name)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(
            f"{self.__class__.__name__} является frozen-объектом. "
            f"Запись атрибута '{name}' запрещена."
        )

    def __delattr__(self, name: str) -> None:
        raise AttributeError(
            f"{self.__class__.__name__} является frozen-объектом. "
            f"Удаление атрибута '{name}' запрещено."
        )

    def __repr__(self) -> str:
        loaded = "loaded" if self._entity is not None else "id_only"
        return f"{self.__class__.__name__}(id={self._id!r}, {loaded})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseRelationOne):
            return NotImplemented
        return self._id == other._id and type(self) is type(other)

    def __hash__(self) -> int:
        return hash((type(self), self._id))


class BaseRelationMany(Generic[T]):
    """
    Базовый контейнер связи «ко многим» (Many).

    Хранит кортеж идентификаторов связанных сущностей (ids) и опционально
    кортеж загруженных объектов (entities). Поддерживает итерацию,
    индексный доступ и len().

    Frozen после создания. Запись и удаление атрибутов запрещены.

    Подклассы (CompositeMany, AggregateMany, AssociationMany) отличаются
    только значением класс-атрибута relation_type.

    Атрибуты:
        ids : tuple[Any, ...]
            Кортеж идентификаторов связанных сущностей. Может быть пустым.

        entities : tuple[T, ...]
            Кортеж загруженных объектов. Может быть пустым, если менеджер
            загрузил только идентификаторы.

        relation_type : RelationType
            Тип владения. Определяется в подклассах.
    """

    __slots__ = ("_entities", "_ids")

    relation_type: RelationType  # Определяется в подклассах

    def __init__(
        self,
        *,
        ids: tuple[Any, ...] = (),
        entities: tuple[T, ...] = (),
    ) -> None:
        """
        Инициализирует контейнер связи «ко многим».

        Аргументы:
            ids: кортеж идентификаторов связанных сущностей.
            entities: кортеж загруженных объектов. Может быть пустым.
        """
        object.__setattr__(self, "_ids", ids)
        object.__setattr__(self, "_entities", entities)

    @property
    def ids(self) -> tuple[Any, ...]:
        """Кортеж идентификаторов связанных сущностей."""
        return self._ids

    @property
    def entities(self) -> tuple[T, ...]:
        """Кортеж загруженных объектов (может быть пустым)."""
        return self._entities

    @property
    def is_loaded(self) -> bool:
        """True если хотя бы один объект загружен."""
        return len(self._entities) > 0

    def __len__(self) -> int:
        """Количество идентификаторов (не загруженных объектов)."""
        return len(self._ids)

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[T, ...]: ...

    def __getitem__(self, index: int | slice) -> T | tuple[T, ...]:
        """
        Индексный доступ к загруженным объектам.

        Аргументы:
            index: целочисленный индекс или срез.

        Возвращает:
            Один объект (при int) или кортеж объектов (при slice).

        Исключения:
            RelationNotLoadedError: если объекты не загружены.
            IndexError: если индекс вне диапазона.
        """
        if not self._entities:
            raise RelationNotLoadedError(
                container_class_name=self.__class__.__name__,
                attribute_name=f"[{index}]",
                entity_id=self._ids,
            )
        result = self._entities[index]
        if isinstance(index, slice):
            return tuple(result)  # type: ignore[arg-type]
        return result  # type: ignore[return-value]

    def __iter__(self):  # type: ignore[override]
        """
        Итерация по загруженным объектам.

        Исключения:
            RelationNotLoadedError: если объекты не загружены.
        """
        if not self._entities:
            raise RelationNotLoadedError(
                container_class_name=self.__class__.__name__,
                attribute_name="__iter__",
                entity_id=self._ids,
            )
        return iter(self._entities)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(
            f"{self.__class__.__name__} является frozen-объектом. "
            f"Запись атрибута '{name}' запрещена."
        )

    def __delattr__(self, name: str) -> None:
        raise AttributeError(
            f"{self.__class__.__name__} является frozen-объектом. "
            f"Удаление атрибута '{name}' запрещено."
        )

    def __repr__(self) -> str:
        count = len(self._ids)
        loaded = len(self._entities)
        return f"{self.__class__.__name__}(count={count}, loaded={loaded})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseRelationMany):
            return NotImplemented
        return self._ids == other._ids and type(self) is type(other)

    def __hash__(self) -> int:
        return hash((type(self), self._ids))


# ═════════════════════════════════════════════════════════════════════════════
# Конкретные контейнеры: Composition
# ═════════════════════════════════════════════════════════════════════════════


class CompositeOne(BaseRelationOne[T]):
    """
    Контейнер связи «к одному» с семантикой Composition.

    Composition — сильное владение. Дочерний объект не существует без
    родителя. При удалении родителя дочерние объекты удаляются.

    ArchiMate: Composition relationship.

    Обратная сторона Composite-связи обязана быть Association (не Composite
    и не Aggregate). Координатор проверяет по матрице совместимости.

    Пример:
        # Заказ владеет адресом доставки (один адрес, удаляется с заказом):
        shipping_address: Annotated[
            CompositeOne[AddressEntity],
            Inverse(AddressEntity, "order"),
        ] = Rel(description="Адрес доставки")
    """

    relation_type = RelationType.COMPOSITION


class CompositeMany(BaseRelationMany[T]):
    """
    Контейнер связи «ко многим» с семантикой Composition.

    Composition — сильное владение. Дочерние объекты не существуют без
    родителя. При удалении родителя все дочерние удаляются.

    ArchiMate: Composition relationship.

    Пример:
        # Заказ владеет позициями (позиции удаляются с заказом):
        items: Annotated[
            CompositeMany[OrderItemEntity],
            Inverse(OrderItemEntity, "order"),
        ] = Rel(description="Позиции заказа")
    """

    relation_type = RelationType.COMPOSITION


# ═════════════════════════════════════════════════════════════════════════════
# Конкретные контейнеры: Aggregation
# ═════════════════════════════════════════════════════════════════════════════


class AggregateOne(BaseRelationOne[T]):
    """
    Контейнер связи «к одному» с семантикой Aggregation.

    Aggregation — слабое владение. Дочерний объект может существовать
    самостоятельно. При удалении родителя дочерний отвязывается.

    ArchiMate: Aggregation relationship.

    Обратная сторона Aggregate-связи обязана быть Association.

    Пример:
        # Команда агрегирует лидера (лидер существует без команды):
        leader: Annotated[
            AggregateOne[EmployeeEntity],
            Inverse(EmployeeEntity, "led_team"),
        ] = Rel(description="Лидер команды")
    """

    relation_type = RelationType.AGGREGATION


class AggregateMany(BaseRelationMany[T]):
    """
    Контейнер связи «ко многим» с семантикой Aggregation.

    Aggregation — слабое владение. Дочерние объекты могут существовать
    самостоятельно. При удалении родителя дочерние отвязываются.

    ArchiMate: Aggregation relationship.

    Пример:
        # Команда агрегирует сотрудников (сотрудники существуют без команды):
        members: Annotated[
            AggregateMany[EmployeeEntity],
            Inverse(EmployeeEntity, "team"),
        ] = Rel(description="Члены команды")
    """

    relation_type = RelationType.AGGREGATION


# ═════════════════════════════════════════════════════════════════════════════
# Конкретные контейнеры: Association
# ═════════════════════════════════════════════════════════════════════════════


class AssociationOne(BaseRelationOne[T]):
    """
    Контейнер связи «к одному» с семантикой Association.

    Association — равноправная связь без владения. Удаление одной
    стороны не затрагивает другую.

    ArchiMate: Association relationship.

    Association может быть парой для любого типа связи: Composite,
    Aggregate или другой Association.

    Пример:
        # Заказ ассоциирован с клиентом (клиент существует независимо):
        customer: Annotated[
            AssociationOne[CustomerEntity],
            Inverse(CustomerEntity, "orders"),
        ] = Rel(description="Клиент, оформивший заказ")
    """

    relation_type = RelationType.ASSOCIATION


class AssociationMany(BaseRelationMany[T]):
    """
    Контейнер связи «ко многим» с семантикой Association.

    Association — равноправная связь без владения. Удаление одной
    стороны не затрагивает другую.

    ArchiMate: Association relationship.

    Пример:
        # Клиент ассоциирован с заказами:
        orders: Annotated[
            AssociationMany[OrderEntity],
            Inverse(OrderEntity, "customer"),
        ] = Rel(description="Заказы клиента")
    """

    relation_type = RelationType.ASSOCIATION
