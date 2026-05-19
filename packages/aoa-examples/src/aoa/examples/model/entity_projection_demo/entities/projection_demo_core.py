# packages/aoa-examples/src/aoa/examples/model/entity_projection_demo/entities/projection_demo_core.py
"""
Projection demo customer + order — mutual ``Inverse`` in one module (class-body order).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Two ``@entity`` hosts for PR-5: ``ProjectionDemoCustomerEntity`` and
``ProjectionDemoOrderEntity`` with a real ``AssociationOne`` / ``AssociationMany`` pair.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import (
    AssociationMany,
    AssociationOne,
    BaseEntity,
    Inverse,
    Rel,
)
from aoa.action_machine.intents.entity import entity
from aoa.examples.model.entity_projection_demo.domain import EntityProjectionDemoDomain
from aoa.examples.model.entity_projection_demo.entities.projection_demo_lifecycle import (
    ProjectionDemoCustomerLifecycle,
    ProjectionDemoOrderLifecycle,
)


@entity(description="Demo storefront customer", domain=EntityProjectionDemoDomain)
class ProjectionDemoCustomerEntity(BaseEntity):
    id: str = Field(description="Customer id")
    lifecycle: ProjectionDemoCustomerLifecycle = Field(description="Customer lifecycle")
    name: str = Field(description="Display name")
    email: str = Field(description="Email")

    orders: Annotated[
        AssociationMany[ProjectionDemoOrderEntity],
        Inverse(ProjectionDemoOrderEntity, "customer"),
    ] = Rel(description="Orders for this customer")  # type: ignore[assignment]


@entity(description="Demo storefront order", domain=EntityProjectionDemoDomain)
class ProjectionDemoOrderEntity(BaseEntity):
    id: str = Field(description="Order id")
    lifecycle: ProjectionDemoOrderLifecycle = Field(description="Order lifecycle")
    status: str = Field(description="Fulfillment status label")
    total: float = Field(description="Order total", ge=0)

    customer: Annotated[
        AssociationOne[ProjectionDemoCustomerEntity],
        Inverse(ProjectionDemoCustomerEntity, "orders"),
    ] = Rel(description="Buyer")  # type: ignore[assignment]


ProjectionDemoCustomerEntity.model_rebuild()
ProjectionDemoOrderEntity.model_rebuild()
