# packages/aoa-examples/src/aoa/examples/model/entity_projection_demo/actions/__init__.py
"""Projection demo actions."""

from __future__ import annotations

from aoa.examples.model.entity_projection_demo.actions.order_wire_preview import ProjectionDemoOrderWirePreviewAction

ProjectionDemoOrderWirePreviewParams = ProjectionDemoOrderWirePreviewAction.Params
ProjectionDemoOrderWirePreviewResult = ProjectionDemoOrderWirePreviewAction.Result

__all__ = [
    "ProjectionDemoOrderWirePreviewAction",
    "ProjectionDemoOrderWirePreviewParams",
    "ProjectionDemoOrderWirePreviewResult",
]
