# packages/aoa-demo/src/aoa/demo/model/entity_projection_demo/entities/projection_demo_core.py
"""
Projection demo customer + order — mutual ``Inverse`` in one module (class-body order).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Two ``@entity`` hosts for PR-5: ``ProjectionDemoCustomerCoreEntity`` and
``ProjectionDemoOrderCoreEntity`` with a real ``AssociationOne`` / ``AssociationMany`` pair.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationMany, AssociationOne, BaseCoreEntity, Inverse, Rel
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.entity_projection_demo.domain import EntityProjectionDemoDomain
from aoa.demo.model.entity_projection_demo.entities.projection_demo_lifecycle import (
    ProjectionDemoCustomerLifecycle,
    ProjectionDemoOrderLifecycle,
)


@entity(description="Demo storefront customer", domain=EntityProjectionDemoDomain)
class ProjectionDemoCustomerCoreEntity(BaseCoreEntity):
    id: str = Field(description="Customer id")
    lifecycle: ProjectionDemoCustomerLifecycle = Field(description="Customer lifecycle")
    name: str = Field(description="Display name")
    email: str = Field(description="Email")

    orders: Annotated[
        AssociationMany[ProjectionDemoOrderCoreEntity],
        Inverse(ProjectionDemoOrderCoreEntity, "customer"),
    ] = Rel(
        description="Orders for this customer"
    )  # type: ignore[assignment]


@entity(description="Demo storefront order", domain=EntityProjectionDemoDomain)
class ProjectionDemoOrderCoreEntity(BaseCoreEntity):
    id: str = Field(description="Order id")
    lifecycle: ProjectionDemoOrderLifecycle = Field(description="Order lifecycle")
    status: str = Field(description="Fulfillment status label")
    total: float = Field(description="Order total", ge=0)

    customer: Annotated[
        AssociationOne[ProjectionDemoCustomerCoreEntity],
        Inverse(ProjectionDemoCustomerCoreEntity, "orders"),
    ] = Rel(
        description="Buyer"
    )  # type: ignore[assignment]


ProjectionDemoCustomerCoreEntity.model_rebuild()
ProjectionDemoOrderCoreEntity.model_rebuild()
