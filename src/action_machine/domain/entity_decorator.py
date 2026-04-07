# src/action_machine/domain/entity_decorator.py
"""
Декоратор @entity — объявление сущности доменной модели.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @entity — единая точка входа для объявления сущности в доменной
модели ActionMachine. Он выполняет три функции одновременно:

1. ПРОВЕРКА GATE-HOST: целевой класс обязан наследовать EntityGateHost.
   BaseEntity наследует его автоматически. Попытка применить @entity
   к голому классу → EntityDecoratorError.

2. ЗАПИСЬ МЕТАДАННЫХ: записывает словарь _entity_info на класс с ключами
   "description" и "domain". Координатор сущностей (EntityCoordinator)
   читает этот словарь при сборке метаданных.

3. РЕГИСТРАЦИЯ: координатор обнаруживает сущность по наличию _entity_info
   при вызове get_metadata() или register(). Декоратор сам НЕ вызывает
   координатор — он только записывает атрибут.

═══════════════════════════════════════════════════════════════════════════════
ОТЛИЧИЕ ОТ @meta
═══════════════════════════════════════════════════════════════════════════════

Для Action и ResourceManager используется декоратор @meta. Для сущностей —
@entity. Это разные декораторы с разными gate-host:

    @meta   → ActionMetaGateHost или ResourceMetaGateHost
    @entity → EntityGateHost

Причины разделения:
- Сущности живут в доменной подсистеме, Action — в ядре. Смешивание
  gate-host создаёт ненужную связность.
- @entity записывает _entity_info, @meta записывает _meta_info.
  Координаторы читают разные атрибуты.
- Сущности не имеют аспектов, ролей, зависимостей — им не нужна
  логика MetadataBuilder из ядра.

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТРЫ
═══════════════════════════════════════════════════════════════════════════════

    description : str
        Обязательный. Текстовое описание сущности: что она представляет
        в бизнес-модели. Непустая строка после strip(). Описание попадает
        в ArchiMate-диаграммы, OCEL-схемы и автогенерированную документацию.
        Пустая строка или строка из пробелов → ValueError.

    domain : type[BaseDomain] | None
        Опциональная привязка к бизнес-домену. Если указан — проверяется,
        что это подкласс BaseDomain. None означает отсутствие привязки.
        В strict-режиме координатора domain может быть обязательным.

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ (ИНВАРИАНТЫ)
═══════════════════════════════════════════════════════════════════════════════

- Применяется только к классам, не к функциям, методам или свойствам.
- Класс должен наследовать EntityGateHost (через BaseEntity или напрямую).
- description — непустая строка (str), после strip() не пустая.
- domain — подкласс BaseDomain или None.
- Порядок декораторов не имеет значения. @entity записывает атрибуты
  независимо от других декораторов.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @entity(description="Заказ клиента", domain=ShopDomain)
        │
        ▼  Декоратор записывает в cls._entity_info
    {"description": "Заказ клиента", "domain": ShopDomain}
        │
        ▼  EntityCoordinator.get_metadata(cls)
    Читает cls._entity_info → EntityMetadata
        │
        ▼  Граф координатора
    Узел entity обогащается description и domain.
    Создаётся узел domain с ребром belongs_to (если domain указан).

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.domain import BaseEntity, BaseDomain
    from action_machine.domain.entity_decorator import entity
    from pydantic import Field

    class ShopDomain(BaseDomain):
        name = "shop"
        description = "Интернет-магазин"

    @entity(description="Заказ клиента", domain=ShopDomain)
    class OrderEntity(BaseEntity):
        id: str = Field(description="Идентификатор заказа")
        amount: float = Field(description="Сумма заказа", ge=0)
        status: str = Field(description="Текущий статус")

    # Без домена:
    @entity(description="Настройка системы")
    class SettingEntity(BaseEntity):
        key: str = Field(description="Ключ настройки")
        value: str = Field(description="Значение настройки")

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    EntityDecoratorError — декоратор применён не к классу; класс не наследует
                           EntityGateHost; description не строка или пуста;
                           domain не подкласс BaseDomain и не None.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.domain.base_domain import BaseDomain
from action_machine.domain.entity_gate_host import EntityGateHost
from action_machine.domain.exceptions import EntityDecoratorError

# ═════════════════════════════════════════════════════════════════════════════
# Валидация аргументов (вынесена для снижения цикломатической сложности)
# ═════════════════════════════════════════════════════════════════════════════


def _validate_entity_description(description: Any) -> None:
    """
    Проверяет корректность параметра description.

    Аргументы:
        description: значение, переданное в @entity.

    Исключения:
        EntityDecoratorError: если description не строка или пуста.
    """
    if not isinstance(description, str):
        raise EntityDecoratorError(
            f"@entity: параметр description должен быть строкой, "
            f"получен {type(description).__name__}: {description!r}."
        )

    if not description.strip():
        raise EntityDecoratorError(
            "@entity: description не может быть пустой строкой. "
            "Укажите описание сущности, например: "
            '@entity(description="Заказ клиента").'
        )


def _validate_entity_domain(domain: Any) -> None:
    """
    Проверяет корректность параметра domain.

    Аргументы:
        domain: значение, переданное в @entity.

    Исключения:
        EntityDecoratorError: если domain не None и не подкласс BaseDomain.
    """
    if domain is None:
        return

    if not isinstance(domain, type):
        raise EntityDecoratorError(
            f"@entity: параметр domain должен быть подклассом BaseDomain или None, "
            f"получен {type(domain).__name__}: {domain!r}. "
            f"Передайте класс домена, например: domain=ShopDomain."
        )

    if not issubclass(domain, BaseDomain):
        raise EntityDecoratorError(
            f"@entity: параметр domain должен быть подклассом BaseDomain, "
            f"получен {domain.__name__}. Класс {domain.__name__} не наследует "
            f"BaseDomain. Создайте домен: class {domain.__name__}(BaseDomain): "
            f'name = "...".'
        )


def _validate_entity_target(cls: Any) -> None:
    """
    Проверяет, что декоратор применяется к классу с EntityGateHost.

    Аргументы:
        cls: объект, к которому применяется декоратор.

    Исключения:
        EntityDecoratorError: если cls не класс или не наследует EntityGateHost.
    """
    if not isinstance(cls, type):
        raise EntityDecoratorError(
            f"@entity можно применять только к классу. "
            f"Получен объект типа {type(cls).__name__}: {cls!r}."
        )

    if not issubclass(cls, EntityGateHost):
        raise EntityDecoratorError(
            f"@entity применён к классу {cls.__name__}, который не наследует "
            f"EntityGateHost. Наследуйте BaseEntity: "
            f"class {cls.__name__}(BaseEntity): ..."
        )


# ═════════════════════════════════════════════════════════════════════════════
# Основной декоратор
# ═════════════════════════════════════════════════════════════════════════════


def entity(
    description: str,
    *,
    domain: type[BaseDomain] | None = None,
) -> Callable[[type], type]:
    """
    Декоратор уровня класса. Объявляет сущность доменной модели.

    Записывает словарь _entity_info в целевой класс. Координатор сущностей
    (EntityCoordinator) читает этот словарь при сборке метаданных.

    Аргументы:
        description: обязательное текстовое описание сущности. Непустая строка.
                     Что представляет сущность в бизнес-модели.
        domain: опциональная привязка к бизнес-домену. Подкласс BaseDomain
                или None.

    Возвращает:
        Декоратор, который записывает _entity_info в класс и возвращает
        класс без изменений.

    Исключения:
        EntityDecoratorError:
            - description не строка или пуста.
            - domain не None и не подкласс BaseDomain.
            - Декоратор применён не к классу.
            - Класс не наследует EntityGateHost.

    Пример:
        @entity(description="Заказ клиента", domain=ShopDomain)
        class OrderEntity(BaseEntity):
            id: str = Field(description="Идентификатор заказа")
            amount: float = Field(description="Сумма заказа", ge=0)
    """
    # ── Проверка аргументов декоратора ──
    _validate_entity_description(description)
    _validate_entity_domain(domain)

    def decorator(cls: type) -> type:
        """
        Внутренний декоратор, применяемый к целевому классу.

        Проверяет:
        1. cls — класс (type).
        2. cls наследует EntityGateHost.

        Затем записывает _entity_info в cls.
        """
        _validate_entity_target(cls)

        cls._entity_info = {  # type: ignore[attr-defined]
            "description": description,
            "domain": domain,
        }

        return cls

    return decorator
