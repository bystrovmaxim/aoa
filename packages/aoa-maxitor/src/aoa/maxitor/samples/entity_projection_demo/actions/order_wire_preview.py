# packages/aoa-maxitor/src/aoa/maxitor/samples/entity_projection_demo/actions/order_wire_preview.py
"""
Sample action returning a partial ``ProjectionDemoOrderEntity`` JSON projection.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.maxitor.samples.entity_projection_demo.domain import EntityProjectionDemoDomain
from aoa.maxitor.samples.entity_projection_demo.entities.projection_demo_core import (
    ProjectionDemoOrderEntity,
)

_ORDER_WIRE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "status": {"type": "string"},
        "total": {"type": "number"},
    },
    "required": ["id", "status", "total"],
    "additionalProperties": False,
}


@meta(
    description="Return a partial order JSON projection (entity wire schema sample)",
    domain=EntityProjectionDemoDomain,
)
@check_roles(NoneRole)
class ProjectionDemoOrderWirePreviewAction(
    BaseAction["ProjectionDemoOrderWirePreviewAction.Params", "ProjectionDemoOrderWirePreviewAction.Result"],
):
    class Params(BaseParams):
        label: str = Field(default="demo", description="Echo label for the stub response")

    class Result(BaseResult):
        label: str = Field(description="Echo of params label")
        order: ProjectionDemoOrderEntity.schema(schema=_ORDER_WIRE_SCHEMA) = Field(
            description="Partial order wire (id, status, total) without nested customer",
        )

    @summary_aspect("Preview order wire")
    async def preview_order_wire_summary(
        self,
        params: ProjectionDemoOrderWirePreviewAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> ProjectionDemoOrderWirePreviewAction.Result:
        return ProjectionDemoOrderWirePreviewAction.Result(
            label=params.label,
            order={"id": "ord-demo-1", "status": "confirmed", "total": 42.5},
        )
