"""Name a kind for readers of the graph.

A kind base class declares its display name in its own body as ``KIND_LABEL``; the export
writes it next to the kind word. AOA's six kinds are named Core, Association, Detail,
Specialization, Enumeration and State. A model may declare a kind of its own; it must name
it, or the class is refused when it is created.

Run: uv run python examples/step_20_entity/27_kind_label.py
"""

from abc import ABC
from typing import Any, ClassVar

from aoa.action_machine.domain import (
    BaseAssocEntity,
    BaseCoreEntity,
    BaseDetailEntity,
    BaseEntity,
    BaseEnumEntity,
    BaseSpecEntity,
    BaseStateEntity,
)
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.exceptions.declaration_structure_error import DeclarationStructureError
from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.graph.nodes.entity_graph_node import EntityGraphNode
from aoa.action_machine.intents.entity import entity


class ShopDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "shop"
    description = "Shop model"


# 1. The six kinds AOA ships, and the names their kind bases declare.
for base in (BaseCoreEntity, BaseAssocEntity, BaseDetailEntity, BaseSpecEntity, BaseEnumEntity, BaseStateEntity):
    print(f"{base.__name__:<18} KIND_LABEL = {base.__dict__['KIND_LABEL']!r}")


# 2. A kind of the model's own: a kind base inherits BaseEntity directly, defines its own
#    __init_subclass__, and names its kind.
@exclude_graph_model
class BaseAggregateEntity(BaseEntity, ABC):
    """An aggregate root of this model."""

    KIND_LABEL: ClassVar[str] = "Aggregate"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Hold every descendant to the kind's name suffix."""
        super().__init_subclass__(**kwargs)
        super()._require_kind_suffix("AggregateEntity")


@exclude_graph_model
@entity(description="Customer order", domain=ShopDomain)
class OrderAggregateEntity(BaseAggregateEntity):
    """Describe an order as an aggregate root."""


row = EntityGraphNode(OrderAggregateEntity).to_dict()["properties"]
print("graph row:", {"entity_kind": row["entity_kind"], "entity_kind_label": row["entity_kind_label"]})


# 3. A kind base that does not name its kind is refused when the class is created.
try:

    class BaseEventEntity(BaseEntity, ABC):
        """A kind with no display name."""

        def __init_subclass__(cls, **kwargs: Any) -> None:
            """Hold every descendant to the kind's name suffix."""
            super().__init_subclass__(**kwargs)

except DeclarationStructureError as error:
    print("refused:", error)
else:
    raise AssertionError("A kind base must name its kind")
