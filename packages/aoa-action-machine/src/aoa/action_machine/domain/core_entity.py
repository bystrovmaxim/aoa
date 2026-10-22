# packages/aoa-action-machine/src/aoa/action_machine/domain/core_entity.py
"""
BaseCoreEntity — the base class of the core kind: an independent domain object.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One of the six base classes a real entity inherits from. It states what an
instance represents in the domain, declares its kind as one word, and holds its
descendants to the kind's name suffix. The other five are declared beside it in this
package, one file each, and the entity base holds the hierarchy rules.

═══════════════════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════════════════

    @entity(description="Customer order", domain=ShopDomain)
    class SalesOrderCoreEntity(BaseCoreEntity):
        id: str = Field(description="Order id")
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model


@exclude_graph_model
class BaseCoreEntity(BaseEntity, ABC):
    """
    An independent domain object with its own domain identity.

    AI-CORE-BEGIN
        ROLE: An object the domain treats as a thing in its own right — an order, a customer, a product, a contract, a supplier offer.
        CONTRACT: Its identity persists when attributes, relationships or state change. It may carry a Lifecycle and head a Specialization.
        INVARIANTS: Must not declare a Generalization; must not be a technical link, an owner's part or variant data of another object.
    AI-CORE-END
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Hold every descendant to the kind's name suffix."""
        super().__init_subclass__(**kwargs)
        super()._require_kind_suffix("CoreEntity")
