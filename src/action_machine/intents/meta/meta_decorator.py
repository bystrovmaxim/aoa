# src/action_machine/intents/meta/meta_decorator.py
"""
``@meta`` — human-readable description and **mandatory** domain binding on a
class.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Part of the ActionMachine intent grammar. Stores a non-empty description and a
``BaseDomain`` subclass on the class. Metadata feeds the coordinator graph and
logging via ``resolve_domain``. Typical hosts are actions and resource managers,
but the decorator only requires a class target.

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
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Classes only (not functions, methods, or properties).
- Target must be a class (``type``).
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
        ▼  MetaIntentInspector snapshot + ``meta`` graph node
        │
        ▼  GraphCoordinator.build()
    Action node enriched; domain node with ``belongs_to`` edge.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    @meta(description="Create a new order", domain=OrdersDomain)
    @check_roles(ManagerRole)
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
        ...

    @meta(description="Ping dependency", domain=SystemDomain)
    @check_roles(NoneRole)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        ...

    @meta(description="PostgreSQL connection manager", domain=WarehouseDomain)
    class WarehouseDbManager(BaseResourceManager):
        ...

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

``TypeError`` — not a class; ``description`` not ``str``; ``domain`` missing,
``None``, or not a ``BaseDomain`` subclass.

``ValueError`` — empty / whitespace ``description``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Class-level description + domain metadata decorator.
CONTRACT: @meta(description=..., domain=...) keyword-only domain required.
INVARIANTS: Class target; domain required.
FLOW: validate → attach _meta_info → graph consumers (logging, coordinator).
FAILURES: TypeError/ValueError as above.
EXTENSION POINTS: graph side consumed by inspectors only.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from action_machine.domain.base_domain import BaseDomain


def _validate_meta_description(description: Any) -> None:
    """Ensure ``description`` is a non-empty string."""
    if not isinstance(description, str):
        raise TypeError(
            f"@meta: description must be str, got {type(description).__name__}: "
            f"{description!r}."
        )

    if not description.strip():
        raise ValueError(
            '@meta: description cannot be empty or whitespace-only. '
            'Example: @meta(description="Creates a new order", domain=MyDomain).'
        )


def _validate_meta_domain(domain: Any) -> None:
    """Ensure ``domain`` is a ``BaseDomain`` subclass."""
    if domain is None:
        raise TypeError(
            "@meta: domain is required (keyword-only). "
            "Pass a BaseDomain subclass, e.g. domain=OrdersDomain."
        )

    if not isinstance(domain, type):
        raise TypeError(
            f"@meta: domain must be a BaseDomain subclass, got "
            f"{type(domain).__name__}: {domain!r}."
        )

    if not issubclass(domain, BaseDomain):
        raise TypeError(
            f"@meta: domain must be a BaseDomain subclass; {domain.__name__!r} "
            f"is not."
        )


def _validate_meta_target(cls: Any) -> None:
    """Ensure ``@meta`` is applied only to classes."""
    if not isinstance(cls, type):
        raise TypeError(
            f"@meta applies only to classes, got {type(cls).__name__}: {cls!r}."
        )


def meta(
    description: str,
    *,
    domain: type[Any],
) -> Callable[[type], type]:
    """
    Class decorator: attach ``_meta_info`` with description and domain.

    ``MetaIntentInspector`` and ``GraphCoordinator.get_snapshot(cls, \"meta\")``
    consume the same scratch written here.

    AI-CORE-BEGIN
    ROLE: Write class-level metadata consumed by graph/runtime inspectors.
    CONTRACT: Validate arguments and attach ``_meta_info`` to target class.
    INVARIANTS: Applies only to classes.
    AI-CORE-END
    """
    _validate_meta_description(description)
    _validate_meta_domain(domain)

    def decorator(cls: type) -> type:
        _validate_meta_target(cls)

        cls._meta_info = {  # type: ignore[attr-defined]
            "description": description,
            "domain": domain,
        }

        return cls

    return decorator
