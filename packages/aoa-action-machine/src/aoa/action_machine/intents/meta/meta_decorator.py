# packages/aoa-action-machine/src/aoa/action_machine/intents/meta/meta_decorator.py
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
    Keyword-only. Required on every host but a data source: there it is omitted
    or ``None`` → ``TypeError`` when the class is decorated. Must be a ``BaseDomain``
    subclass; a wrong type → ``TypeError``. A data source (``BaseDataSource``) has
    no domain, and one given → ``TypeError``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @meta(description="Create a new order", domain=OrdersDomain)
        │
        ▼  writes cls._meta_info
    {"description": "...", "domain": OrdersDomain}
        │
        ▼  ``MetaIntentResolver`` + ``ActionGraphNode`` wiring
        │
        ▼  ``NodeGraphCoordinator.build()``
    Action node enriched; domain node with ``belongs_to`` edge.

"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.decorator_argument_type_error import DecoratorArgumentTypeError
from aoa.action_machine.exceptions.decorator_target_error import DecoratorTargetError
from aoa.action_machine.exceptions.description_contract_error import DescriptionContractError
from aoa.action_machine.exceptions.description_type_error import DescriptionTypeError


def _validate_meta_description(description: Any) -> None:
    """Ensure ``description`` is a non-empty string."""
    if not isinstance(description, str):
        raise DescriptionTypeError(f"@meta: description must be str, got {type(description).__name__}: " f"{description!r}.")

    if not description.strip():
        raise DescriptionContractError(
            "@meta: description cannot be empty or whitespace-only. "
            'Example: @meta(description="Creates a new order", domain=MyDomain).'
        )


def _validate_meta_domain(domain: Any) -> None:
    """Ensure ``domain`` is a ``BaseDomain`` subclass."""
    if domain is None:
        raise DecoratorArgumentTypeError(
            "@meta: domain is required (keyword-only). " "Pass a BaseDomain subclass, e.g. domain=OrdersDomain."
        )

    if not isinstance(domain, type):
        raise DecoratorArgumentTypeError(f"@meta: domain must be a BaseDomain subclass, got " f"{type(domain).__name__}: {domain!r}.")

    if not issubclass(domain, BaseDomain):
        raise DecoratorArgumentTypeError(f"@meta: domain must be a BaseDomain subclass; {domain.__name__!r} " f"is not.")


def _validate_meta_target(cls: Any) -> None:
    """Ensure ``@meta`` is applied only to classes."""
    if not isinstance(cls, type):
        raise DecoratorTargetError(f"@meta applies only to classes, got {type(cls).__name__}: {cls!r}.")


def _validate_meta_host_domain(cls: type, domain: Any) -> None:
    """A data source has no domain; every other host has one."""
    # Imported here: the resources package itself imports this decorator's intent.
    from aoa.action_machine.resources.base_data_source import BaseDataSource  # pylint: disable=import-outside-toplevel

    if issubclass(cls, BaseDataSource):
        if domain is not None:
            raise DecoratorArgumentTypeError(
                f"@meta on {cls.__name__}: a data source has no domain — it is physical, and resources "
                "of several domains may share it. Remove domain=."
            )
        return
    _validate_meta_domain(domain)


def meta(
    description: str,
    *,
    domain: type[Any] | None = None,
) -> Callable[[type], type]:
    """
    Class decorator: attach ``_meta_info`` with description and domain.

    ``domain`` is required on every host but a data source (``BaseDataSource``), which has none.

    :class:`~aoa.action_machine.intents.meta.meta_intent_resolver.MetaIntentResolver` and
    action graph export consume the same scratch written here.

    AI-CORE-BEGIN
    ROLE: Write class-level metadata consumed by graph/runtime inspectors.
    CONTRACT: Validate arguments and attach ``_meta_info`` to target class.
    INVARIANTS: Applies only to classes.
    AI-CORE-END
    """
    _validate_meta_description(description)
    if domain is not None:
        _validate_meta_domain(domain)

    def decorator(cls: type) -> type:
        _validate_meta_target(cls)
        _validate_meta_host_domain(cls, domain)

        cls._meta_info = {  # type: ignore[attr-defined]
            "description": description,
            "domain": domain,
        }

        return cls

    return decorator
