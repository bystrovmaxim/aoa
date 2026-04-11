# src/action_machine/core/meta_decorator.py
"""
Decorator @meta — объявление описания и доменной принадлежности класса.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator @meta — часть грамматики намерений ActionMachine. Он объявляет
обязательное текстовое описание класса (что это и зачем) и привязку к
бизнес-домену там, где она требуется инвариантом (см. ниже). Описание
хранится в runtime metadata и попадает в граф координатора.

@meta применяется к двум типам классов:
1. Действия (Action) — наследники BaseAction через ActionMetaGateHost.
2. Ресурсные менеджеры — наследники BaseResourceManager через ResourceMetaGateHost.

Decorator при применении проверяет, что целевой класс наследует хотя бы
один из двух гейт-хостов (ActionMetaGateHost или ResourceMetaGateHost).
Если ни один не найден — TypeError.

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    description : str
        Обязательный. Что делает действие или ресурсный менеджер.
        Непустая строка после strip(). Пустая строка или строка
        из пробелов — ValueError.

    domain : type[BaseDomain]
        Подкласс ``BaseDomain``. **Обязательный** keyword-only параметр; без него
        вызов ``@meta`` невозможен.

═══════════════════════════════════════════════════════════════════════════════
LIMITATIONS (INVARIANTS)
═══════════════════════════════════════════════════════════════════════════════

- Применяется только к классам, не к функциям, methodам или свойствам.
- Class должен наследовать ActionMetaGateHost или ResourceMetaGateHost.
- description — непустая строка (str), после strip() не пустая.
- domain — подкласс BaseDomain (всегда обязателен).
- Повторное применение @meta к одному классу перезаписывает предыдущее.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @meta(description="Создание нового заказа", domain=OrdersDomain)
        │
        ▼  Decorator записывает в cls._meta_info
    {"description": "Создание нового заказа", "domain": OrdersDomain}
        │
        ▼  MetaGateHostInspector.Snapshot + узел ``meta`` в графе
        │
        ▼  GateCoordinator.build() — commit графа
    Узел action обогащается description и domain.
    Создаётся узел domain с ребром belongs_to.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # Действие с привязкой к домену:
    @meta(description="Создание нового заказа", domain=OrdersDomain)
    @check_roles("manager")
    @depends(PaymentService)
    @connection(PostgresManager, key="db")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        ...

    # Действие без аспектов — domain всё равно обязателен:
    @meta(description="Проверка доступности сервиса", domain=SystemDomain)
    @check_roles(ROLE_NONE)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        ...

    # Ресурсный менеджер:
    @meta(description="Менеджер соединений с PostgreSQL", domain=WarehouseDomain)
    class WarehouseDbManager(BaseResourceManager):
        ...

═══════════════════════════════════════════════════════════════════════════════
ERRORS
═══════════════════════════════════════════════════════════════════════════════

    TypeError — декоратор применён не к классу; класс не наследует ни один
               из гейт-хостов; description не строка; domain не передан, None
               или не подкласс BaseDomain.
    ValueError — description пустая строка или строка из пробелов.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.core.meta_gate_hosts import ActionMetaGateHost, ResourceMetaGateHost
from action_machine.domain.base_domain import BaseDomain

# ═════════════════════════════════════════════════════════════════════════════
# Validation аргументов (вынесена для снижения цикломатической сложности)
# ═════════════════════════════════════════════════════════════════════════════


def _validate_meta_description(description: Any) -> None:
    """
    Checks корректность параметра description.

    Args:
        description: значение, переданное в @meta.

    Raises:
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
    Checks корректность параметра domain.

    Args:
        domain: значение, переданное в @meta.

    Raises:
        TypeError: если domain is None или не подкласс BaseDomain.
    """
    if domain is None:
        raise TypeError(
            "@meta: параметр domain обязателен. Укажите подкласс BaseDomain, "
            "например: domain=OrdersDomain."
        )

    if not isinstance(domain, type):
        raise TypeError(
            f"@meta: параметр domain должен быть подклассом BaseDomain, "
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
    Checks, что декоратор применяется к классу с подходящим гейт-хостом.

    Args:
        cls: объект, к которому применяется декоратор.

    Raises:
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
    domain: type[BaseDomain],
) -> Callable[[type], type]:
    """
    Decorator уровня класса. Объявляет описание и доменную принадлежность.

    Записывает словарь _meta_info в целевой класс. Инспектор ``meta`` строит
    снимок и узел графа; ``GateCoordinator.get_snapshot(cls, \"meta\")`` отдаёт
    этот снимок.

    Args:
        description: обязательное текстовое описание класса. Непустая строка.
                     Что делает действие или ресурсный менеджер.
        domain: подкласс BaseDomain (обязательный keyword-only аргумент).

    Returns:
        Decorator, который записывает _meta_info в класс и возвращает
        класс без изменений.

    Raises:
        TypeError:
            - description не строка.
            - domain не передан, None или не подкласс BaseDomain.
            - Decorator применён не к классу.
            - Class не наследует ActionMetaGateHost и не наследует
              ResourceMetaGateHost.
        ValueError:
            - description пустая строка или строка из пробелов.

    Пример:
        @meta(description="Создание нового заказа", domain=OrdersDomain)
        @check_roles("manager")
        class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
            ...

        @meta(description="Менеджер соединений с PostgreSQL", domain=WarehouseDomain)
        class PostgresManager(BaseResourceManager):
            ...
    """
    # ── Проверка аргументов декоратора ──
    _validate_meta_description(description)
    _validate_meta_domain(domain)

    def decorator(cls: type) -> type:
        """
        Внутренний декоратор, применяемый к целевому классу.

        Checks:
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
