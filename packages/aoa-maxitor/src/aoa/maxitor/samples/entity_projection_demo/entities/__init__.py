# packages/aoa-maxitor/src/aoa/maxitor/samples/entity_projection_demo/entities/__init__.py
"""Projection demo entities (import for registration side effects)."""

from __future__ import annotations

from aoa.maxitor.samples.entity_projection_demo.entities.projection_demo_core import (
    ProjectionDemoCustomerEntity,
    ProjectionDemoOrderEntity,
)

__all__ = [
    "ProjectionDemoCustomerEntity",
    "ProjectionDemoOrderEntity",
]
