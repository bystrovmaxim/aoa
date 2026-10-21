"""Reject a status field without a JSON representation.

Export a state whose custom field cannot be serialized.

Run: uv run python examples/step_22_lifecycle/19_non_json_field.py
"""

from pydantic import ConfigDict, Field
from pydantic_core import PydanticSerializationError
from aoa.action_machine.domain import BaseEntity, BaseStateEntity, Lifecycle, StateVocabulary
from aoa.action_machine.graph.nodes.lifecycle_graph_node import LifeCycleGraphNode


class Opaque:
    """Provide no JSON representation."""


class OrderStateEntity(BaseStateEntity):
    """Allow a Python object that has no JSON form."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    value: Opaque = Field(description="An opaque Python value")


class OrderLifecycle(Lifecycle, StateVocabulary):
    """Use otherwise valid transitions."""
    DRAFT = OrderStateEntity(code="draft", display_name="Draft", value=Opaque())
    PAID = OrderStateEntity(code="paid", display_name="Paid", value=Opaque())
    _template = Lifecycle().state(DRAFT).to(PAID).initial().state(PAID).final()


class OrderEntity(BaseEntity):
    """Host the lifecycle used for graph export."""
    lifecycle: OrderLifecycle = Field(description="Current order state")

# Run the case.
try:
    LifeCycleGraphNode(OrderEntity, "lifecycle", OrderLifecycle)
except PydanticSerializationError as error:
    print(type(error).__name__ + ": " + str(error))
else:
    raise AssertionError("The invalid declaration was accepted")
