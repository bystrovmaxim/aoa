# packages/aoa-action-machine/src/aoa/action_machine/domain/assoc_entity.py
"""
BaseAssocEntity — the base class of the assoc kind: a technical link without domain data.

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

    @entity(description="Product category membership", domain=ShopDomain)
    class ProductCategoryAssocEntity(BaseAssocEntity):
        product_id: str = Field(description="Linked product")
        category_id: str = Field(description="Linked category")
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model


@exclude_graph_model
class BaseAssocEntity(BaseEntity, ABC):
    """
    A technical link whose domain meaning is only its participants.

    AI-CORE-BEGIN
        ROLE: A degenerate association with no domain data of its own — it records only that two or more objects are connected.
        CONTRACT: Participant references and service fields (``id``, ``created_at``, ``updated_at``) are allowed; the link is not an owned part and is not an independent object.
        INVARIANTS: No Lifecycle, no Specialization head, no Generalization, never a Composite target. Price, quantity, terms or responsibilities mean the class is a core entity instead.
    AI-CORE-END
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Hold every descendant to the kind's name suffix."""
        super().__init_subclass__(**kwargs)
        super()._require_kind_suffix("AssocEntity")
