# src/action_machine/domain/relation_markers.py
"""
Маркеры связей доменной модели: Inverse, NoInverse, Rel.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит три компонента, используемых при объявлении связей между
сущностями в доменной модели ActionMachine:

1. Inverse — маркер обратной связи. Указывает, какое поле целевой сущности
   является парой для данной связи.

2. NoInverse — маркер отсутствия обратной связи. Явное указание, что
   у данной связи нет парного поля на целевой сущности.

3. Rel — дескриптор описания связи. Содержит обязательное текстовое
   описание связи и используется как значение по умолчанию для поля.

Каждая связь между сущностями обязана иметь:
- Контейнер связи (CompositeOne, AssociationMany и т.д.) — тип поля.
- Inverse или NoInverse — в Annotated-аннотации.
- Rel(description="...") — как значение поля (default).

Отсутствие Inverse или NoInverse — ошибка сборки координатора.
Отсутствие Rel — ошибка сборки координатора.

═══════════════════════════════════════════════════════════════════════════════
ПОЧЕМУ INVERSE ОБЯЗАТЕЛЕН
═══════════════════════════════════════════════════════════════════════════════

Автоматический поиск обратных связей ломается при дублировании типов.
Если у сущности Customer есть два поля orders и invoices, оба типа
AssociationMany[OrderEntity], координатор не сможет определить, какое
из них является парой для OrderEntity.customer. Явный Inverse — одна
строка, которая делает связь однозначной, читаемой и безопасной при
рефакторинге.

═══════════════════════════════════════════════════════════════════════════════
ПОЧЕМУ ОПИСАНИЕ ОБЯЗАТЕЛЬНО
═══════════════════════════════════════════════════════════════════════════════

Каждая связь обязана иметь текстовое описание. Описание — структурное
метаданное, которое попадёт в ArchiMate-диаграмму, OCEL-схему и
автогенерированную документацию. Если связь двусторонняя (есть Inverse) —
обе стороны обязаны иметь Rel(description). Координатор проверяет при
сборке.

═══════════════════════════════════════════════════════════════════════════════
СИНТАКСИС ОБЪЯВЛЕНИЯ СВЯЗИ
═══════════════════════════════════════════════════════════════════════════════

    from typing import Annotated
    from action_machine.domain import (
        AssociationOne, AssociationMany, Inverse, NoInverse, Rel,
    )

    @entity(description="Заказ клиента", domain=ShopDomain)
    class OrderEntity(BaseEntity):
        # Двусторонняя связь: OrderEntity.customer ↔ CustomerEntity.orders
        customer: Annotated[
            AssociationOne[CustomerEntity],
            Inverse(CustomerEntity, "orders"),
        ] = Rel(description="Клиент, оформивший заказ")

    @entity(description="Клиент", domain=ShopDomain)
    class CustomerEntity(BaseEntity):
        # Обратная сторона связи
        orders: Annotated[
            AssociationMany[OrderEntity],
            Inverse(OrderEntity, "customer"),
        ] = Rel(description="Заказы клиента")

    # Односторонняя связь (без обратной стороны):
    @entity(description="Лог аудита", domain=AuditDomain)
    class AuditLogEntity(BaseEntity):
        target: Annotated[
            AssociationOne[OrderEntity],
            NoInverse(),
        ] = Rel(description="Объект аудита")

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    Annotated[AssociationOne[CustomerEntity], Inverse(CustomerEntity, "orders")]
        │
        ▼  EntityCoordinator при сборке метаданных
    Извлекает из аннотации: контейнер, Inverse/NoInverse
    Извлекает из значения поля: Rel(description)
        │
        ▼  Проверки координатора
    1. Inverse-пара существует на целевой сущности.
    2. Обе стороны имеют Rel(description).
    3. Типы владения совместимы (матрица).
        │
        ▼  Граф координатора
    Рёбра между узлами entity с типом связи (composition/aggregation/association).
"""

from __future__ import annotations

from typing import Any


class Inverse:
    """
    Маркер обратной связи в Annotated-аннотации поля сущности.

    Указывает координатору, какое поле целевой сущности является парой
    для данной связи. Координатор при сборке метаданных проверяет:
    1. Целевая сущность существует и зарегистрирована.
    2. Указанное поле существует на целевой сущности.
    3. Поле целевой сущности является контейнером связи.
    4. Типы владения совместимы (матрица).
    5. Обе стороны имеют Rel(description).

    Inverse — frozen-объект. После создания изменение невозможно.

    Атрибуты:
        target_entity : type
            Класс целевой сущности (наследник BaseEntity).
            Используется координатором для поиска обратной стороны.

        field_name : str
            Имя поля на целевой сущности, являющегося обратной стороной
            связи. Координатор проверяет его существование и тип.

    Пример:
        customer: Annotated[
            AssociationOne[CustomerEntity],
            Inverse(CustomerEntity, "orders"),
        ] = Rel(description="Клиент, оформивший заказ")
    """

    __slots__ = ("_field_name", "_target_entity")

    def __init__(self, target_entity: type, field_name: str) -> None:
        """
        Инициализирует маркер обратной связи.

        Аргументы:
            target_entity: класс целевой сущности (наследник BaseEntity).
            field_name: имя поля на целевой сущности.

        Исключения:
            TypeError: если target_entity не является классом.
            TypeError: если field_name не является строкой.
            ValueError: если field_name — пустая строка.
        """
        if not isinstance(target_entity, type):
            raise TypeError(
                f"Inverse: target_entity должен быть классом, "
                f"получен {type(target_entity).__name__}: {target_entity!r}."
            )

        if not isinstance(field_name, str):
            raise TypeError(
                f"Inverse: field_name должен быть строкой, "
                f"получен {type(field_name).__name__}: {field_name!r}."
            )

        if not field_name.strip():
            raise ValueError(
                "Inverse: field_name не может быть пустой строкой."
            )

        object.__setattr__(self, "_target_entity", target_entity)
        object.__setattr__(self, "_field_name", field_name)

    @property
    def target_entity(self) -> type:
        """Класс целевой сущности."""
        return self._target_entity

    @property
    def field_name(self) -> str:
        """Имя поля на целевой сущности."""
        return self._field_name

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Inverse является frozen-объектом. Запись запрещена.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Inverse является frozen-объектом. Удаление запрещено.")

    def __repr__(self) -> str:
        return f"Inverse({self._target_entity.__name__}, '{self._field_name}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Inverse):
            return NotImplemented
        return (
            self._target_entity is other._target_entity
            and self._field_name == other._field_name
        )

    def __hash__(self) -> int:
        return hash((id(self._target_entity), self._field_name))


class NoInverse:
    """
    Маркер отсутствия обратной связи в Annotated-аннотации поля сущности.

    Явное указание, что у данной связи нет парного поля на целевой
    сущности. Это НЕ умолчание — каждая связь обязана иметь либо
    Inverse, либо NoInverse. Отсутствие обоих — ошибка сборки координатора.

    NoInverse используется для односторонних связей, когда обратная
    навигация не нужна или не имеет смысла:

    - Лог аудита → целевой объект (логу не нужна обратная ссылка).
    - Настройка → создатель (настройке не нужен список создателей).
    - Уведомление → получатель (получателю не нужен список уведомлений
      в модели, хотя в БД связь может существовать).

    NoInverse — frozen-объект без атрибутов.

    Пример:
        target: Annotated[
            AssociationOne[OrderEntity],
            NoInverse(),
        ] = Rel(description="Объект аудита")
    """

    __slots__ = ()

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("NoInverse является frozen-объектом. Запись запрещена.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("NoInverse является frozen-объектом. Удаление запрещено.")

    def __repr__(self) -> str:
        return "NoInverse()"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NoInverse):
            return NotImplemented
        return True

    def __hash__(self) -> int:
        return hash("NoInverse")


class Rel:
    """
    Дескриптор описания связи. Используется как значение по умолчанию
    для поля-связи сущности.

    Содержит обязательное текстовое описание связи в данном направлении.
    Описание попадает в ArchiMate-диаграммы, OCEL-схемы и автогенерированную
    документацию. Если связь двусторонняя (Inverse) — обе стороны обязаны
    иметь Rel(description). Координатор проверяет при сборке.

    Rel — frozen-объект. После создания изменение невозможно.

    Rel используется Pydantic как default-значение поля. При создании
    экземпляра сущности через конструктор или partial() поле-связь
    получает фактическое значение (контейнер связи), а Rel остаётся
    только в определении класса как метаданное.

    Атрибуты:
        description : str
            Текстовое описание связи в данном направлении.
            Непустая строка. Обязательна.

    Пример:
        customer: Annotated[
            AssociationOne[CustomerEntity],
            Inverse(CustomerEntity, "orders"),
        ] = Rel(description="Клиент, оформивший заказ")
    """

    __slots__ = ("_description",)

    def __init__(self, *, description: str) -> None:
        """
        Инициализирует дескриптор описания связи.

        Аргументы:
            description: текстовое описание связи. Обязательный keyword-only
                         параметр. Непустая строка.

        Исключения:
            TypeError: если description не строка.
            ValueError: если description — пустая строка.
        """
        if not isinstance(description, str):
            raise TypeError(
                f"Rel: description должен быть строкой, "
                f"получен {type(description).__name__}: {description!r}."
            )

        if not description.strip():
            raise ValueError(
                "Rel: description не может быть пустой строкой. "
                "Укажите описание связи."
            )

        object.__setattr__(self, "_description", description)

    @property
    def description(self) -> str:
        """Текстовое описание связи."""
        return self._description

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("Rel является frozen-объектом. Запись запрещена.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError("Rel является frozen-объектом. Удаление запрещено.")

    def __repr__(self) -> str:
        return f"Rel(description='{self._description}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rel):
            return NotImplemented
        return self._description == other._description

    def __hash__(self) -> int:
        return hash(self._description)
