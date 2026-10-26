# packages/aoa-action-machine/src/aoa/action_machine/domain/detail_entity.py
"""
BaseDetailEntity — the base class of the detail kind: an identifiable part of one owner.

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

    @entity(description="A line of one order", domain=ShopDomain)
    class OrderLineDetailEntity(BaseDetailEntity):
        order_id: str = Field(description="Owning order")
        number: int = Field(description="Line number within the order")

    These fields identify the part; the complete example also declares ownership
    with relation containers in examples/step_20_entity/05_detail.py.
"""

from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar

from aoa.action_machine.domain.entity import BaseEntity
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model


@exclude_graph_model
class BaseDetailEntity(BaseEntity, ABC):
    """
    An identifiable part whose existence and identity depend on its owner.

    AI-CORE-BEGIN
        ROLE: A part of one owner — an order line, a recipe step — identified by the owner plus a discriminator within that owner.
        CONTRACT: It may carry domain data of its own, a Lifecycle, nested details and specializations; a separate database id does not make it independent. Its display name in the graph is ``KIND_LABEL`` = "Detail".
        INVARIANTS: Does not exist after its owner ceases to exist; does not declare a Generalization; a specialization of it reuses its complete identity and adds no identity component.
    AI-CORE-END
    """

    KIND_LABEL: ClassVar[str] = "Detail"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Hold every descendant to the kind's name suffix."""
        super().__init_subclass__(**kwargs)
        super()._require_kind_suffix("DetailEntity")
