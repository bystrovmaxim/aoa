# src/action_machine/core/meta_decorator.py
"""
Декоратор @meta — объявление описания и доменной принадлежности класса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @meta — часть грамматики намерений ActionMachine. Он объявляет
обязательное текстовое описание класса (что это и зачем) и опциональную
привязку к бизнес-домену. Описание хранится в ClassMetadata и попадает
в граф координатора.

@meta применяется к двум типам классов:
1. Действия (Action) — наследники BaseAction через ActionMetaGateHost.
2. Ресурсные менеджеры — наследники BaseResourceManager через ResourceMetaGateHost.

Декоратор при применении проверяет, что целевой класс наследует хотя бы
один из двух гейт-хостов (ActionMetaGateHost или ResourceMetaGateHost).
Если ни один не найден — TypeError.

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТРЫ
═══════════════════════════════════════════════════════════════════════════════

    description : str
        Обязательный. Что делает действие или ресурсный менеджер.
        Непустая строка после strip(). Пустая строка или строка
        из пробелов — ValueError.

    domain : type[BaseDomain] | None
        Опциональная привязка к бизнес-домену. Если указан — проверяется,
        что это подкласс BaseDomain. None означает отсутствие привязки.
        В strict-режиме координатора domain обязателен.

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ (ИНВАРИАНТЫ)
═══════════════════════════════════════════════════════════════════════════════

- Применяется только к классам, не к функциям, методам или свойствам.
- Класс должен наследовать ActionMetaGateHost или ResourceMetaGateHost.
- description — непустая строка (str), после strip() не пустая.
- domain — подкласс BaseDomain или None.
- Повторное применение @meta к одному классу перезаписывает предыдущее.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @meta(description="Создание нового заказа", domain=OrdersDomain)
        │
        ▼  Декоратор записывает в cls._meta_info
    {"description": "Создание нового заказа", "domain": OrdersDomain}
        │
        ▼  MetadataBuilder → collectors.collect_meta(cls)
    ClassMetadata.meta = MetaInfo(description="...", domain=OrdersDomain)
        │
        ▼  GateCoordinator._populate_graph()
    Узел action обогащается description и domain.
    Создаётся узел domain с ребром belongs_to.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Действие с привязкой к домену:
    @meta(description="Создание нового заказа", domain=OrdersDomain)
    @check_roles("manager")
    @depends(PaymentService)
    @connection(PostgresManager, key="db")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        ...

    # Действие без домена:
    @meta(description="Проверка доступности сервиса")
    @check_roles(ROLE_NONE)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        ...

    # Ресурсный менеджер:
    @meta(description="Менеджер соединений с PostgreSQL", domain=WarehouseDomain)
    class WarehouseDbManager(BaseResourceManager):
        ...

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    TypeError — декоратор применён не к классу; класс не наследует ни один
               из гейт-хостов; description не строка; domain не подкласс
               BaseDomain и не None.
    ValueError — description пустая строка или строка из пробелов.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.core.meta_gate_hosts import ActionMetaGateHost, ResourceMetaGateHost
from action_machine.domain.base_domain import BaseDomain

# ═════════════════════════════════════════════════════════════════════════════
# Валидация аргументов (вынесена для снижения цикломатической сложности)
# ═════════════════════════════════════════════════════════════════════════════


def _validate_meta_description(description: Any) -> None:
    """
    Проверяет корректность параметра description.

    Аргументы:
        description: значение, переданное в @meta.

    Исключения:
        TypeError: если description не строка.
        ValueError: если description пустая строка или строка из пробелов.
    """
    if not isinstance(description, str):
        raise TypeError(
            f"@meta: параметр description должен быть строкой, "
            f"получен {type(description).__name__}: {description!r}."
        )

    if not description.strip():
        raise ValueError(
            "@meta: description не может быть пустой строкой. "
            "Укажите описание класса, например: "
            '@meta(description="Создание нового заказа").'
        )


def _validate_meta_domain(domain: Any) -> None:
    """
    Проверяет корректность параметра domain.

    Аргументы:
        domain: значение, переданное в @meta.

    Исключения:
        TypeError: если domain не None и не подкласс BaseDomain.
    """
    if domain is None:
        return

    if not isinstance(domain, type):
        raise TypeError(
            f"@meta: параметр domain должен быть подклассом BaseDomain или None, "
            f"получен {type(domain).__name__}: {domain!r}. "
            f"Передайте класс домена, например: domain=OrdersDomain."
        )

    if not issubclass(domain, BaseDomain):
        raise TypeError(
            f"@meta: параметр domain должен быть подклассом BaseDomain, "
            f"получен {domain.__name__}. Класс {domain.__name__} не наследует "
            f"BaseDomain. Создайте домен: class {domain.__name__}(BaseDomain): "
            f'name = "...".'
        )


def _validate_meta_target(cls: Any) -> None:
    """
    Проверяет, что декоратор применяется к классу с подходящим гейт-хостом.

    Аргументы:
        cls: объект, к которому применяется декоратор.

    Исключения:
        TypeError: если cls не класс, или не наследует ни ActionMetaGateHost,
                   ни ResourceMetaGateHost.
    """
    if not isinstance(cls, type):
        raise TypeError(
            f"@meta можно применять только к классу. "
            f"Получен объект типа {type(cls).__name__}: {cls!r}."
        )

    is_action_host = issubclass(cls, ActionMetaGateHost)
    is_resource_host = issubclass(cls, ResourceMetaGateHost)

    if not is_action_host and not is_resource_host:
        raise TypeError(
            f"@meta применён к классу {cls.__name__}, который не наследует "
            f"ни ActionMetaGateHost, ни ResourceMetaGateHost. "
            f"Декоратор @meta разрешён только для наследников BaseAction "
            f"и BaseResourceManager."
        )


# ═════════════════════════════════════════════════════════════════════════════
# Основной декоратор
# ═════════════════════════════════════════════════════════════════════════════


def meta(
    description: str,
    *,
    domain: type[BaseDomain] | None = None,
) -> Callable[[type], type]:
    """
    Декоратор уровня класса. Объявляет описание и доменную принадлежность.

    Записывает словарь _meta_info в целевой класс. MetadataBuilder читает
    этот словарь при сборке ClassMetadata.meta (MetaInfo). GateCoordinator
    использует MetaInfo для обогащения узлов графа и создания доменных узлов.

    Аргументы:
        description: обязательное текстовое описание класса. Непустая строка.
                     Что делает действие или ресурсный менеджер.
        domain: опциональная привязка к бизнес-домену. Подкласс BaseDomain
                или None. В strict-режиме координатора domain обязателен.

    Возвращает:
        Декоратор, который записывает _meta_info в класс и возвращает
        класс без изменений.

    Исключения:
        TypeError:
            - description не строка.
            - domain не None и не подкласс BaseDomain.
            - Декоратор применён не к классу.
            - Класс не наследует ActionMetaGateHost и не наследует
              ResourceMetaGateHost.
        ValueError:
            - description пустая строка или строка из пробелов.

    Пример:
        @meta(description="Создание нового заказа", domain=OrdersDomain)
        @check_roles("manager")
        class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
            ...

        @meta(description="Менеджер соединений с PostgreSQL")
        class PostgresManager(BaseResourceManager):
            ...
    """
    # ── Проверка аргументов декоратора ──
    _validate_meta_description(description)
    _validate_meta_domain(domain)

    def decorator(cls: type) -> type:
        """
        Внутренний декоратор, применяемый к целевому классу.

        Проверяет:
        1. cls — класс (type).
        2. cls наследует ActionMetaGateHost или ResourceMetaGateHost.

        Затем записывает _meta_info в cls.
        """
        _validate_meta_target(cls)

        cls._meta_info = { # type: ignore[attr-defined]
            "description": description,
            "domain": domain,
        }

        return cls

    return decorator
