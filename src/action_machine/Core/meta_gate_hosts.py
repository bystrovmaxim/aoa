# src/action_machine/core/meta_gate_hosts.py
"""
Модуль: ActionMetaGateHost и ResourceMetaGateHost — маркерные миксины
для декоратора @meta.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator @meta применяется к двум различным иерархиям классов:

1. Действия (Action) — наследники BaseAction.
2. Ресурсные менеджеры (ResourceManager) — наследники BaseResourceManager.

Эти иерархии не пересекаются. Для каждой создан свой marker mixin,
который разрешает применение @meta и обеспечивает контроль обязательности.

ActionMetaGateHost — наследуется BaseAction. Обозначает, что класс действия
обязан иметь декоратор @meta с описанием. MetadataBuilder при сборке
метаданных проверяет: если класс наследует ActionMetaGateHost и содержит
аспекты — @meta обязателен. Без него — TypeError.

ResourceMetaGateHost — наследуется BaseResourceManager. Обозначает, что
класс ресурсного менеджера обязан иметь декоратор @meta с описанием.
MetadataBuilder проверяет аналогично: если класс наследует
ResourceMetaGateHost — @meta обязателен.

Decorator @meta при применении проверяет, что целевой класс наследует
хотя бы один из двух гейт-хостов. Если ни один не найден — TypeError.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    class BaseAction[P, R](
        ABC,
        RoleGateHost,
        DependencyGateHost[object],
        CheckerGateHost,
        AspectGateHost,
        ConnectionGateHost,
        ActionMetaGateHost,             ← маркер: @meta обязателен
    ): ...

    class BaseResourceManager(ABC, ResourceMetaGateHost):
        ...                             ← маркер: @meta обязателен

    @meta(description="Создание заказа", domain=OrdersDomain)
    @check_roles("manager")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        ...

    @meta(description="Менеджер PostgreSQL")
    class PostgresManager(BaseResourceManager):
        ...

    # Decorator @meta проверяет:
    #   issubclass(cls, ActionMetaGateHost) or issubclass(cls, ResourceMetaGateHost)
    #   → True → OK, записывает cls._meta_info = {"description": ..., "domain": ...}

    # MetadataBuilder.build(cls) проверяет:
    #   Если класс наследует ActionMetaGateHost и имеет аспекты → _meta_info обязателен.
    #   Если класс наследует ResourceMetaGateHost → _meta_info обязателен.

═══════════════════════════════════════════════════════════════════════════════
ПРИНЦИПЫ
═══════════════════════════════════════════════════════════════════════════════

1. ДВА ГЕЙТ-ХОСТА, ОДИН ДЕКОРАТОР. Единый декоратор @meta обслуживает
   обе иерархии. Гейт-хосты разделены, потому что BaseAction и
   BaseResourceManager — независимые деревья наследования.

2. МАРКЕРЫ БЕЗ ЛОГИКИ. Миксины не содержат полей, methodов или логики.
   Их единственная функция — разрешение применения @meta и контроль
   обязательности через issubclass().

3. ОБЯЗАТЕЛЬНОСТЬ. Наличие гейт-хоста в MRO класса означает, что
   @meta ОБЯЗАТЕЛЕН. Это безусловный инвариант: нельзя создать действие
   или ресурсный менеджер без описания.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # BaseAction уже наследует ActionMetaGateHost:
    @meta(description="Пинг-проверка", domain=InfraDomain)
    @check_roles(ROLE_NONE)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        @summary_aspect("Pong")
        async def pong(self, params, state, box, connections):
            return BaseResult()

    # BaseResourceManager уже наследует ResourceMetaGateHost:
    @meta(description="Менеджер соединений Redis")
    class RedisManager(BaseResourceManager):
        def get_wrapper_class(self):
            return None

    # Без @meta — error при сборке метаданных:
    class BadAction(BaseAction[BaseParams, BaseResult]):
        @summary_aspect("Broken")
        async def broken(self, params, state, box, connections):
            return BaseResult()
    # MetadataBuilder.build(BadAction) → TypeError:
    # "Action BadAction не имеет декоратора @meta.
    #  Добавьте @meta(description=\"...\")."
"""

from __future__ import annotations

from typing import Any, ClassVar


class ActionMetaGateHost:
    """
    Marker mixin, обозначающий обязательность декоратора @meta
    для классов действий (Action).

    Наследуется BaseAction. Class, наследующий ActionMetaGateHost
    и содержащий аспекты, обязан иметь декоратор @meta с описанием.
    MetadataBuilder проверяет это при сборке runtime metadata.

    Миксин не содержит логики, полей или methodов. Его функция —
    служить проверочным маркером для issubclass() в декораторе @meta
    и в валидаторах MetadataBuilder.

    Атрибуты уровня класса (создаются динамически декоратором @meta):
        _meta_info : dict[str, Any]
            Словарь {"description": str, "domain": type[BaseDomain] | None},
            записываемый декоратором @meta. Читается MetadataBuilder
            при сборке снимка ``meta`` в графе координатора.
    """

    _meta_info: ClassVar[dict[str, Any]]


class ResourceMetaGateHost:
    """
    Marker mixin, обозначающий обязательность декоратора @meta
    для классов ресурсных менеджеров (ResourceManager).

    Наследуется BaseResourceManager. Class, наследующий
    ResourceMetaGateHost, обязан иметь декоратор @meta с описанием.
    MetadataBuilder проверяет это при сборке runtime metadata.

    Миксин не содержит логики, полей или methodов. Его функция —
    служить проверочным маркером для issubclass() в декораторе @meta
    и в валидаторах MetadataBuilder.

    Атрибуты уровня класса (создаются динамически декоратором @meta):
        _meta_info : dict[str, Any]
            Словарь {"description": str, "domain": type[BaseDomain] | None},
            записываемый декоратором @meta. Читается MetadataBuilder
            при сборке снимка ``meta`` в графе координатора.
    """

    _meta_info: ClassVar[dict[str, Any]]


def validate_meta_required(
    cls: type,
    has_meta_info: bool,
    aspects: list[Any],
) -> None:
    """Инварианты ActionMetaGateHost / ResourceMetaGateHost для @meta."""
    if has_meta_info:
        return

    if issubclass(cls, ActionMetaGateHost) and aspects:
        raise TypeError(
            f"Action {cls.__name__} не имеет декоратора @meta. "
            f"Каждое действие обязано иметь описание. "
            f'Добавьте @meta(description="...") перед определением класса.'
        )
    if issubclass(cls, ResourceMetaGateHost):
        raise TypeError(
            f"Ресурсный менеджер {cls.__name__} не имеет декоратора @meta. "
            f"Каждый ресурсный менеджер обязан иметь описание. "
            f'Добавьте @meta(description="...") перед определением класса.'
        )
