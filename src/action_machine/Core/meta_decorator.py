# src/action_machine/core/meta_decorator.py
"""
``@meta`` — human description plus **mandatory** domain binding for gated classes.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Part of the ActionMachine intent grammar. Stores a non-empty description and a
``BaseDomain`` subclass on the class. Metadata feeds the coordinator graph and
logging via ``resolve_domain``.

Applies only to:

1. Actions — ``BaseAction`` subclasses using ``ActionMetaGateHost``.
2. Resource managers — ``BaseResourceManager`` subclasses using
   ``ResourceMetaGateHost``.

The decorator requires at least one of those gate hosts; otherwise
``TypeError``.

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

``description : str``
    Required. What the action or manager does. Non-empty after ``strip()``;
    whitespace-only → ``ValueError``.

``domain : type[BaseDomain]``
    Required **keyword-only** argument (no default). Must be a ``BaseDomain``
    subclass. Omitted, ``None``, or wrong type → ``TypeError``.

═══════════════════════════════════════════════════════════════════════════════
LIMITATIONS (INVARIANTS)
═══════════════════════════════════════════════════════════════════════════════

- Classes only (not functions, methods, or properties).
- Target must inherit ``ActionMetaGateHost`` or ``ResourceMetaGateHost``.
- Re-applying ``@meta`` overwrites prior metadata on the same class.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @meta(description="Create a new order", domain=OrdersDomain)
        │
        ▼  writes cls._meta_info
    {"description": "...", "domain": OrdersDomain}
        │
        ▼  MetaGateHostInspector snapshot + ``meta`` graph node
        │
        ▼  GateCoordinator.build()
    Action node enriched; domain node with ``belongs_to`` edge.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    @meta(description="Create a new order", domain=OrdersDomain)
    @check_roles("manager")
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        ...

    @meta(description="Ping dependency", domain=SystemDomain)
    @check_roles(ROLE_NONE)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        ...

    @meta(description="PostgreSQL connection manager", domain=WarehouseDomain)
    class WarehouseDbManager(BaseResourceManager):
        ...

═══════════════════════════════════════════════════════════════════════════════
ERRORS
═══════════════════════════════════════════════════════════════════════════════

``TypeError`` — not a class; missing gate host; ``description`` not ``str``;
``domain`` missing, ``None``, or not a ``BaseDomain`` subclass.

``ValueError`` — empty / whitespace ``description``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Class-level description + domain metadata decorator.
CONTRACT: @meta(description=..., domain=...) keyword-only domain required.
INVARIANTS: gate-host check; domain never optional.
FLOW: validate → attach _meta_info → graph consumers (logging, coordinator).
FAILURES: TypeError/ValueError as above.
EXTENSION POINTS: graph side consumed by inspectors only.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
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
