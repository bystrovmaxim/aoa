# packages/aoa-demo/src/aoa/demo/model/entity_projection_demo/entities/projection_demo_lifecycle.py
# pylint: disable=undefined-variable  # the class-name alias is the declaration surface
"""
Minimal lifecycles for projection demo entities.
"""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class ProjectionDemoCustomerStateEntity(BaseStateEntity):
    """Status of the ProjectionDemoCustomer axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    ACTIVE = value(code="active", display_name="Active", sort_order=1)
    ARCHIVED = value(code="archived", display_name="Archived", sort_order=2)



class ProjectionDemoCustomerLifecycle(Lifecycle[ProjectionDemoCustomerStateEntity]):
    """Two-state customer lifecycle for graph inspectors."""


    _template = Lifecycle().state(ProjectionDemoCustomerStateEntity.ACTIVE).to(ProjectionDemoCustomerStateEntity.ARCHIVED).initial().state(ProjectionDemoCustomerStateEntity.ARCHIVED).final()


class ProjectionDemoOrderStateEntity(BaseStateEntity):
    """Status of the ProjectionDemoOrder axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    DRAFT = value(code="draft", display_name="Draft", sort_order=1)
    CONFIRMED = value(code="confirmed", display_name="Confirmed", sort_order=2)
    CANCELLED = value(code="cancelled", display_name="Cancelled", sort_order=3)



class ProjectionDemoOrderLifecycle(Lifecycle[ProjectionDemoOrderStateEntity]):
    """Order lifecycle aligned with storefront-style status names."""


    _template = (
        Lifecycle()
        .state(ProjectionDemoOrderStateEntity.DRAFT)
        .to(ProjectionDemoOrderStateEntity.CONFIRMED)
        .initial()
        .state(ProjectionDemoOrderStateEntity.CONFIRMED)
        .to(ProjectionDemoOrderStateEntity.CANCELLED)
        .intermediate()
        .state(ProjectionDemoOrderStateEntity.CANCELLED)
        .final()
    )
