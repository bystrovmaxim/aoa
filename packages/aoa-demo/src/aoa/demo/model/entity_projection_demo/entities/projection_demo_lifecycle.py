# packages/aoa-demo/src/aoa/demo/model/entity_projection_demo/entities/projection_demo_lifecycle.py
"""
Minimal lifecycles for projection demo entities.
"""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    StateVocabulary,
)


class ProjectionDemoCustomerStateEntity(BaseStateEntity):
    """Status of the ProjectionDemoCustomer axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class ProjectionDemoCustomerLifecycle(Lifecycle, StateVocabulary):
    """Two-state customer lifecycle for graph inspectors."""

    ACTIVE = ProjectionDemoCustomerStateEntity(code="active", display_name="Active", sort_order=1)
    ARCHIVED = ProjectionDemoCustomerStateEntity(code="archived", display_name="Archived", sort_order=2)

    _template = Lifecycle().state(ACTIVE).to(ARCHIVED).initial().state(ARCHIVED).final()


class ProjectionDemoOrderStateEntity(BaseStateEntity):
    """Status of the ProjectionDemoOrder axis."""

    sort_order: int = Field(default=0, description="Presentation order")


class ProjectionDemoOrderLifecycle(Lifecycle, StateVocabulary):
    """Order lifecycle aligned with storefront-style status names."""

    DRAFT = ProjectionDemoOrderStateEntity(code="draft", display_name="Draft", sort_order=1)
    CONFIRMED = ProjectionDemoOrderStateEntity(code="confirmed", display_name="Confirmed", sort_order=2)
    CANCELLED = ProjectionDemoOrderStateEntity(code="cancelled", display_name="Cancelled", sort_order=3)

    _template = (
        Lifecycle()
        .state(DRAFT)
        .to(CONFIRMED)
        .initial()
        .state(CONFIRMED)
        .to(CANCELLED)
        .intermediate()
        .state(CANCELLED)
        .final()
    )
