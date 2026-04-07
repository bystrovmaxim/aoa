# src/action_machine/domain/hydration.py
"""
Утилиты гидратации сущностей.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Модуль предоставляет функцию build() для сборки frozen-сущностей
из плоских словарей данных с типизированным маппингом через лямбду.

build() — основной способ создания сущностей из данных, полученных
из хранилища (БД, API, файлы). Маппинг через EntityProxy обеспечивает
автодополнение полей в IDE.

═══════════════════════════════════════════════════════════════════════════════
ENTITYPROXY — ТИПИЗИРОВАННЫЙ ДОСТУП К ПОЛЯМ
═══════════════════════════════════════════════════════════════════════════════

EntityProxy[T] — прокси-объект, возвращающий имена полей сущности
как строки. Используется внутри маппера build() для типизированного
доступа к полям:

    build(row, OrderEntity, lambda e, r: {
        e.id: r["order_id"],        # e.id → "id"
        e.amount: r["total"],       # e.amount → "amount"
    })

IDE видит тип T и подсказывает поля. При обращении к несуществующему
полю — AttributeError.

═══════════════════════════════════════════════════════════════════════════════
СВЯЗИ И DEFAULT_FACTORY
═══════════════════════════════════════════════════════════════════════════════

Поля связей (AggregateMany, AssociationOne и т.д.) объявляются с
default_factory=list или default=None в Pydantic Field [5]. При создании
сущности через build() без явного указания значения связи Pydantic
использует default_factory и создаёт обычный list [], а не экземпляр
контейнера (AggregateMany и т.д.).

Это ожидаемое поведение: контейнеры связей — аннотации типов для
метаданных координатора (ArchiMate, OCEL), а не runtime-обёртки [5].
Координатор читает аннотацию через get_origin() и извлекает
ownership_type и cardinality.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

Прямой маппинг (ключи словаря совпадают с полями сущности):

    order = build(
        {"id": "ORD-001", "amount": 100.0, "status": "new"},
        OrderEntity,
    )

Маппинг через лямбду (ключи словаря отличаются от полей):

    order = build(row, OrderEntity, lambda e, r: {
        e.id: r["order_id"],
        e.customer: build(r, CustomerEntity, lambda e2, r2: {
            e2.id: r2["customer_id"],
            e2.name: r2["customer_name"],
        }),
    })

Прокси e типизирован — IDE подсказывает поля OrderEntity.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class EntityProxy(Generic[T]):
    """
    Прокси для типизированного доступа к полям сущности в build().

    При обращении к атрибуту возвращает имя поля как строку.
    Используется как первый аргумент маппера в build().

    Атрибуты:
        _cls: класс сущности, поля которого проксируются.

    Пример:
        proxy = EntityProxy(OrderEntity)
        proxy.id      # → "id"
        proxy.amount  # → "amount"
        proxy.foo     # → AttributeError
    """

    def __init__(self, cls: type[T]) -> None:
        self._cls = cls

    def __getattr__(self, name: str) -> str:
        """
        Возвращает имя поля для маппинга.

        Проверяет, что запрашиваемый атрибут является объявленным
        полем модели (model_fields). Если нет — AttributeError [10].

        Аргументы:
            name: имя запрашиваемого атрибута.

        Возвращает:
            str — имя поля (совпадает с name).

        Исключения:
            AttributeError: если поле не объявлено в модели.
        """
        if name in self._cls.model_fields:
            return name
        raise AttributeError(f"'{self._cls.__name__}' has no field '{name}'")


def build(
    data: dict[str, Any],
    entity_cls: type[T],
    mapper: Callable[[EntityProxy[T], dict[str, Any]], dict[str, Any]] | None = None,
) -> T:
    """
    Собирает сущность из плоского словаря с типизированным маппингом.

    Аргументы:
        data:       плоский словарь данных из хранилища.
        entity_cls: класс сущности для создания.
        mapper:     функция маппинга (proxy, data) -> dict полей.
                    Если None — прямой маппинг (ключи data = поля сущности).

    Возвращает:
        T — экземпляр сущности, созданный через конструктор Pydantic
        с полной валидацией типов и обязательности полей.

    Пример прямого маппинга:
        entity = build({"id": "123", "name": "Test", "value": 42}, TestEntity)

    Пример маппинга через лямбду:
        entity = build(row, OrderEntity, lambda e, r: {
            e.id: r["order_id"],
            e.amount: r["total"],
        })
    """
    if mapper is None:
        return entity_cls(**data)

    proxy = EntityProxy(entity_cls)
    mapped = mapper(proxy, data)
    return entity_cls(**mapped)
