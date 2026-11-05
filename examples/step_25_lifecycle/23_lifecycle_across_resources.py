"""Keep a lifecycle inside one resource.

A state type declares no resource of its own: it is stored with the entities whose
``Lifecycle[...]`` uses it. Two entities of one resource may share a state type; entities of
two resources may not, so the model refuses the second one.

Run: uv run python examples/step_25_lifecycle/23_lifecycle_across_resources.py
"""

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity, BaseStateEntity, EntityResourceError, Lifecycle, value
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.entity import entity
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_storage import BaseStorage
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine


class StoreDomain(BaseDomain):
    """Group the shop model declarations."""

    name = "store"
    description = "Store"


@meta(description="Primary relational store", domain=StoreDomain)
class StorefrontDatabase(BaseStorage):
    """The database the orders live in."""


@meta(description="Support desk store", domain=StoreDomain)
class SupportDatabase(BaseStorage):
    """The database the returns live in."""


class OrderStateEntity(BaseStateEntity):
    """Describe one possible order status."""

    DRAFT = value(code="draft", display_name="Draft")
    PAID = value(code="paid", display_name="Paid")


class OrderLifecycle(Lifecycle[OrderStateEntity]):
    """Allow a draft to become paid."""

    _template = (
        Lifecycle()
        .state(OrderStateEntity.DRAFT).to(OrderStateEntity.PAID).initial()
        .state(OrderStateEntity.PAID).final()
    )


@entity(description="Customer order", resource=StorefrontDatabase)
class SalesOrderCoreEntity(BaseCoreEntity):
    """An order with a status."""

    id: str = Field(description="Order identifier")
    lifecycle: OrderLifecycle = Field(description="Order status")


@entity(description="Order copy", resource=StorefrontDatabase)
class OrderCopyCoreEntity(BaseCoreEntity):
    """A copy of the order kept in the same database."""

    id: str = Field(description="Copy identifier")
    lifecycle: OrderLifecycle = Field(description="Copy status")


@entity(description="Return", resource=SupportDatabase)
class ReturnCoreEntity(BaseCoreEntity):
    """A return in another database that reuses the order's statuses."""

    id: str = Field(description="Return identifier")
    lifecycle: OrderLifecycle = Field(description="Return status")


# Run the case.
try:
    ActionProductMachine(loggers=[])
except EntityResourceError as error:
    print(type(error).__name__ + ":", error)
else:
    raise AssertionError("A lifecycle across resources was accepted")
