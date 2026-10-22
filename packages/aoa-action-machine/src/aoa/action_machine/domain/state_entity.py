# packages/aoa-action-machine/src/aoa/action_machine/domain/state_entity.py
"""
BaseStateEntity — the marker of the state kind: a lifecycle status as a domain object.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One of the six base classes a real entity inherits from, and the only one that
carries fields: a status is one state of one lifecycle axis, with a stable
``code`` the machine uses as the state key, a ``display_name`` the diagrams
show, and whatever domain fields the status needs. It is a domain object, not a
transport schema, and it is never an entity of the model graph.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    The kind word, the name rule of the kind, the two required fields and their
    non-blank validation, and the automatic exclusion of every status type from
    the interchange graph.

**Out of scope**
    Collection and lookup — ``StateVocabulary``. Classification and transitions —
    ``Lifecycle``. Persistence and transport — separate work.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    BaseEntity (ABC)   ──►  BaseStateEntity (ABC)  ──►  OrderStateEntity
                              code / display_name        + domain fields
                                  │
                                  ├── lifecycle template: key = code, label = display_name
                                  └── interchange graph: label + properties.attributes

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    class OrderStateEntity(BaseStateEntity):
        sort_order: int = Field(default=0, description="Presentation order")
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from pydantic import Field, field_validator

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model


@exclude_graph_model
class BaseStateEntity(BaseEntity, ABC):
    """
    AI-CORE-BEGIN
        ROLE: Marker of the state kind — a lifecycle status, one state of one axis, carrying its own domain fields.
        CONTRACT: ``code`` is the identity of the status inside ``Lifecycle``; ``display_name`` is the human label carried into the interchange graph; every descendant is kept out of the model graph.
        INVARIANTS: Immutable; ``code`` and ``display_name`` are non-empty after strip; a subclass adds domain fields only, never a second identity or a classification.
    AI-CORE-END
    """

    code: str = Field(description="Stable state code — identity inside the lifecycle")
    display_name: str = Field(description="Human label for UI and diagrams")

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
