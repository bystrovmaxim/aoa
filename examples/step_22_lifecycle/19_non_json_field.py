"""Reject a status field without a JSON representation.

Export a state whose custom field cannot be serialized.

Run: uv run python examples/step_22_lifecycle/19_non_json_field.py
"""

from pydantic import ConfigDict, Field
from pydantic_core import PydanticSerializationError

from aoa.action_machine.domain import BaseCoreEntity, BaseStateEntity, Lifecycle, value
from aoa.action_machine.graph.nodes.lifecycle_graph_node import LifeCycleGraphNode


class Opaque:
    """Provide no JSON representation."""


class OrderStateEntity(BaseStateEntity):
    """Allow a Python object that has no JSON form."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    payload: Opaque = Field(description="An opaque Python value")

    DRAFT = value(code="draft", display_name="Draft", payload=Opaque())
    PAID = value(code="paid", display_name="Paid", payload=Opaque())



class OrderLifecycle(Lifecycle[OrderStateEntity]):
    """Use otherwise valid transitions."""
    _template = Lifecycle().state(OrderStateEntity.DRAFT).to(OrderStateEntity.PAID).initial().state(OrderStateEntity.PAID).final()


class OrderCoreEntity(BaseCoreEntity):
    """Host the lifecycle used for graph export."""
    lifecycle: OrderLifecycle = Field(description="Current order state")

# Run the case.
try:
    LifeCycleGraphNode(OrderCoreEntity, "lifecycle", OrderLifecycle)
except PydanticSerializationError as error:
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid declaration was accepted")
