# packages/aoa-action-machine/src/aoa/action_machine/domain/state_entity.py
"""
BaseStateEntity — the marker of the state kind: a status type that owns its statuses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One of the six base classes a real entity inherits from, and the only one that
carries fields: a status is one state of one lifecycle axis, with a stable
``code`` the machine uses as the state key, a ``display_name`` the diagrams
show, and whatever domain fields the status needs.

The type also declares its own statuses in its own body::

    class OrderStateEntity(BaseStateEntity):
        DRAFT = value(code="draft", display_name="Draft")

``value`` returns a placeholder; after the class is created every name is a real
instance and the type carries the catalogue: ``members``, ``codes()``,
``by_code()`` and ``entity_type``. A class body cannot also bind the name
``value``; a model that needs such a field imports the factory under another
name.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    The kind word, the name rule of the kind, the two required fields and their
    non-blank validation, and the automatic exclusion of every status type from
    the interchange graph. The declaration machinery, the conversion and the
    catalogue come from :mod:`~aoa.action_machine.domain.declared_values`.

**Out of scope**
    Classification and transitions — ``Lifecycle``. The axis checks — the
    generic ``Lifecycle``. Persistence and transport — separate work.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    class body            conversion hook                consumers
    DRAFT = value(...)  ──►  OrderStateEntity(**kwargs)  ──►  members,
    (ValueSpec placeholder)  full instance, validated       codes(), by_code(),
                                                             entity_type
                                  │
                                  ├── lifecycle template: key = code, label = display_name
                                  └── interchange graph: label + properties.attributes

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    class OrderStateEntity(BaseStateEntity):
        sort_order: int = Field(default=0, description="Presentation order")

        DRAFT = value(code="draft", display_name="Draft", sort_order=99)
        PAID = value(code="paid", display_name="Paid", sort_order=1)
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from pydantic import ConfigDict, Field, field_validator

from aoa.action_machine.domain.declared_values import (
    ValueSpec,
    _DeclaredValues,
)
from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model


class BaseStateEntity(_DeclaredValues, BaseEntity, ABC):
    """
    AI-CORE-BEGIN
        ROLE: Marker of the state kind — a status type that declares its own statuses and carries their catalogue.
        CONTRACT: ``code`` is the identity of the status inside ``Lifecycle``; ``display_name`` is the human label carried into the interchange graph; after class creation every declared status is an instance and ``members``, ``codes()``, ``by_code()`` and ``entity_type`` expose the catalogue; every descendant is kept out of the model graph.
        INVARIANTS: Immutable; ``code`` and ``display_name`` are non-empty after strip; statuses share the declaring type; codes are unique; a subclass with no statuses inherits the parent's catalogue; a placeholder is never a model field.
    AI-CORE-END
    """

    model_config = ConfigDict(**BaseEntity.model_config, ignored_types=(ValueSpec,))

    __declared_values_inherit__ = True
    __declared_values_noun__ = "status"

    code: str = Field(description="Stable state code — identity inside the lifecycle")
    display_name: str = Field(description="Human label for UI and diagrams")

    def __init__(self, **data: Any) -> None:  # pylint: disable=useless-parent-delegation
        """Build a status from its validated fields."""
        super().__init__(**data)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Hold every status type to the kind's name suffix and out of the interchange graph."""
        super().__init_subclass__(**kwargs)
        super()._require_kind_suffix("StateEntity")
        exclude_graph_model(cls)

    @field_validator("code", "display_name")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        """Invariant: a code or a label is not empty and not whitespace-only."""
        if not value.strip():
            raise ValueError("A state entity's 'code' and 'display_name' cannot be empty or whitespace-only.")
        return value


exclude_graph_model(BaseStateEntity)
