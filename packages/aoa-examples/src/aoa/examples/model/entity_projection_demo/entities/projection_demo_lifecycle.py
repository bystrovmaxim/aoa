# packages/aoa-examples/src/aoa/examples/model/entity_projection_demo/entities/projection_demo_lifecycle.py
"""
Minimal lifecycles for projection demo entities.
"""

from __future__ import annotations

from aoa.action_machine.domain import Lifecycle


class ProjectionDemoCustomerLifecycle(Lifecycle):
    """Two-state customer lifecycle for graph inspectors."""

    _template = Lifecycle().state("active", "Active").to("archived").initial().state("archived", "Archived").final()


class ProjectionDemoOrderLifecycle(Lifecycle):
    """Order lifecycle aligned with storefront-style status names."""

    _template = (
        Lifecycle()
        .state("draft", "Draft")
        .to("confirmed")
        .initial()
        .state("confirmed", "Confirmed")
        .to("cancelled")
        .intermediate()
        .state("cancelled", "Cancelled")
        .final()
    )
