# packages/aoa-demo/src/aoa/demo/model/entity_projection_demo/entities/__init__.py
"""Projection demo entities (import for registration side effects)."""

from __future__ import annotations

from aoa.demo.model.entity_projection_demo.entities.projection_demo_core import (
    ProjectionDemoCustomerEntity,
    ProjectionDemoOrderEntity,
)

__all__ = [
    "ProjectionDemoCustomerEntity",
    "ProjectionDemoOrderEntity",
]
