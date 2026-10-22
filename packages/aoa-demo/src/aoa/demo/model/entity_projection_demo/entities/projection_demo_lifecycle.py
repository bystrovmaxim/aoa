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
)


class ProjectionDemoCustomerStateEntity(BaseStateEntity):
    """Status of the ProjectionDemoCustomer axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    ACTIVE = ProjectionDemoCustomerStateEntity(code="active", display_name="Active", sort_order=1)  # noqa: F821
    ARCHIVED = ProjectionDemoCustomerStateEntity(code="archived", display_name="Archived", sort_order=2)  # noqa: F821



class ProjectionDemoCustomerLifecycle(Lifecycle[ProjectionDemoCustomerStateEntity]):
    """Two-state customer lifecycle for graph inspectors."""


    _template = Lifecycle().state(ProjectionDemoCustomerStateEntity.ACTIVE).to(ProjectionDemoCustomerStateEntity.ARCHIVED).initial().state(ProjectionDemoCustomerStateEntity.ARCHIVED).final()


class ProjectionDemoOrderStateEntity(BaseStateEntity):
    """Status of the ProjectionDemoOrder axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    DRAFT = ProjectionDemoOrderStateEntity(code="draft", display_name="Draft", sort_order=1)  # noqa: F821
    CONFIRMED = ProjectionDemoOrderStateEntity(code="confirmed", display_name="Confirmed", sort_order=2)  # noqa: F821
    CANCELLED = ProjectionDemoOrderStateEntity(code="cancelled", display_name="Cancelled", sort_order=3)  # noqa: F821



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
