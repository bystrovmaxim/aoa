# src/action_machine/domain/entity_gate_host.py
"""
EntityGateHost — маркерный миксин для декоратора @entity.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

EntityGateHost — миксин-маркер, который разрешает применение декоратора
@entity к классу. Декоратор при применении проверяет:

    if not issubclass(cls, EntityGateHost):
        raise EntityDecoratorError("Класс должен наследовать EntityGateHost")

Без наследования от EntityGateHost декоратор @entity выбросит
EntityDecoratorError. Это защита от случайного применения @entity
к классам, которые не являются сущностями доменной модели.

BaseEntity наследует EntityGateHost автоматически, поэтому разработчику
не нужно указывать его вручную. Но если кто-то попытается повесить
@entity на голый класс — он получит понятную ошибку.

═══════════════════════════════════════════════════════════════════════════════
ПАТТЕРН GATE-HOST
═══════════════════════════════════════════════════════════════════════════════

Gate-host — общий паттерн ActionMachine. Каждый декоратор уровня класса
требует наличия соответствующего маркерного миксина в MRO:

    ActionMetaGateHost       → разрешает @meta для Action
    ResourceMetaGateHost     → разрешает @meta для ResourceManager
    RoleGateHost             → разрешает @check_roles
    DependencyGateHost       → разрешает @depends
    ConnectionGateHost       → разрешает @connection
    EntityGateHost           → разрешает @entity

Миксины не содержат логики — только служат проверочными маркерами
для issubclass(). Это явное согласие разработчика на подключение
функциональности, а не магия.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class BaseEntity(BaseSchema, ABC, EntityGateHost, DescribedFieldsGateHost):
        ...                             ← маркер: разрешает @entity

    @entity(description="Заказ клиента", domain=ShopDomain)
    class OrderEntity(BaseEntity):
        ...

    # Декоратор @entity проверяет:
    #   issubclass(OrderEntity, EntityGateHost) → True → OK
    #   Записывает: cls._entity_info = {"description": ..., "domain": ...}

    # EntityCoordinator при сборке метаданных:
    #   Читает cls._entity_info → EntityMetadata

═══════════════════════════════════════════════════════════════════════════════
АТРИБУТЫ УРОВНЯ КЛАССА
═══════════════════════════════════════════════════════════════════════════════

Декоратор @entity записывает на класс атрибут _entity_info — словарь
с ключами "description" и "domain". Этот атрибут читается координатором
сущностей (EntityCoordinator) при сборке метаданных.

    _entity_info : dict[str, Any]
        {"description": str, "domain": type[BaseDomain] | None}

Атрибут создаётся динамически декоратором @entity, а не объявляется
в EntityGateHost. Аннотация ClassVar указана для mypy.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # BaseEntity уже наследует EntityGateHost — всё работает:
    @entity(description="Клиент", domain=CrmDomain)
    class CustomerEntity(BaseEntity):
        id: str = Field(description="Идентификатор клиента")
        name: str = Field(description="Имя клиента")

    # Попытка применить @entity к голому классу — ошибка:
    @entity(description="Не сущность")
    class NotAnEntity:
        pass
    # → EntityDecoratorError: @entity применён к классу NotAnEntity,
    #   который не наследует EntityGateHost.
"""

from __future__ import annotations

from typing import Any, ClassVar


class EntityGateHost:
    """
    Маркерный миксин, разрешающий использование декоратора @entity.

    Класс, НЕ наследующий EntityGateHost, не может быть целью @entity —
    декоратор выбросит EntityDecoratorError при попытке применения.

    Миксин не содержит логики, полей или методов. Его единственная
    функция — служить проверочным маркером для issubclass() в декораторе
    @entity и в валидаторах координатора сущностей.

    Атрибуты уровня класса (создаются динамически декоратором @entity):
        _entity_info : dict[str, Any]
            Словарь {"description": str, "domain": type[BaseDomain] | None},
            записываемый декоратором @entity. Читается координатором
            сущностей при сборке метаданных.
    """

    _entity_info: ClassVar[dict[str, Any]]
