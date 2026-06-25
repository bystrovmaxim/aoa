# packages/aoa-fastapi-adapter/tests/support/adapter_fixtures.py
"""
Shared adapter-fixture actions for the FastAPI adapter test suite.

════════════════════════════════════════════════════════════════════════════════
PURPOSE
════════════════════════════════════════════════════════════════════════════════

Minimal actions whose ``Result`` (and/or ``Params``) carry schema-backed fields,
used to assert OpenAPI projection and raw-dict round-trips at the HTTP boundary:

- ``EntityProjectionAdapterTestAction`` — ``Result.order`` is a
  ``SampleEntity.schema(...)`` wire projection (object with required id/name,
  ``additionalProperties: False``).
- ``EntityProjectionParamsMcpTestAction`` — sibling whose ``Params`` carry the
  same entity wire projection (kept for parity with the MCP suite).
- ``AdapterTestAction`` — ``Result.graph`` is a ``JsonSchemaValue``-backed
  ``GraphJson`` type (object with required nodes/edges arrays).

The scenario imports point at the in-package :mod:`.domain_model` rather than the
repository-level ``tests`` package.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.model.json_schema_value import JsonSchemaValue
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

from .domain_model import SampleEntity, TestDomain

_SAMPLE_ENTITY_WIRE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
    },
    "required": ["id", "name"],
    "additionalProperties": False,
}


@meta(description="Adapter test action for BaseEntity.schema() transport checks", domain=TestDomain)
@check_roles(GuestRole)
class EntityProjectionAdapterTestAction(
    BaseAction["EntityProjectionAdapterTestAction.Params", "EntityProjectionAdapterTestAction.Result"],
):
    """Minimal action: params carry ``label``; result carries a partial entity wire dict."""

    class Params(BaseParams):
        label: str = Field(description="Label")

    class Result(BaseResult):
        domain: str = Field(description="Domain name")
        order: SampleEntity.schema(schema=_SAMPLE_ENTITY_WIRE_SCHEMA) = Field(  # type: ignore[valid-type]
            description="Partial SampleEntity wire projection",
        )

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: EntityProjectionAdapterTestAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        return EntityProjectionAdapterTestAction.Result(
            domain=params.label,
            order={"id": "e1", "name": "One"},
        )


@meta(
    description="Adapter test action: Params carry BaseEntity.schema() wire projection",
    domain=TestDomain,
)
@check_roles(GuestRole)
class EntityProjectionParamsMcpTestAction(
    BaseAction["EntityProjectionParamsMcpTestAction.Params", "EntityProjectionParamsMcpTestAction.Result"],
):
    """Params include an entity wire projection; Result is minimal (MCP inputSchema coverage)."""

    class Params(BaseParams):
        label: str = Field(description="Label")
        order: SampleEntity.schema(schema=_SAMPLE_ENTITY_WIRE_SCHEMA) = Field(  # type: ignore[valid-type]
            description="Partial SampleEntity wire projection on input",
        )

    class Result(BaseResult):
        echo_domain: str = Field(description="Echo of label")

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: EntityProjectionParamsMcpTestAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        _ = params.order
        return EntityProjectionParamsMcpTestAction.Result(echo_domain=params.label)


_EMPTY_GRAPH_VERTEX: dict[str, Any] = {"type": "object", "properties": {}, "additionalProperties": False}
GraphJson = JsonSchemaValue.define(
    name="GraphJson",
    schema={
        "type": "object",
        "properties": {
            "nodes": {"type": "array", "items": _EMPTY_GRAPH_VERTEX},
            "edges": {"type": "array", "items": _EMPTY_GRAPH_VERTEX},
        },
        "required": ["nodes", "edges"],
        "additionalProperties": False,
    },
)


@meta(description="Adapter test action for JsonSchemaValue transport checks", domain=TestDomain)
@check_roles(GuestRole)
class AdapterTestAction(BaseAction["AdapterTestAction.Params", "AdapterTestAction.Result"]):
    """Minimal action: params carry ``label``; result carries a schema-backed ``graph``."""

    class Params(BaseParams):
        label: str = Field(description="Label")

    class Result(BaseResult):
        domain: str = Field(description="Domain name")
        graph: GraphJson = Field(description="Graph payload")

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: AdapterTestAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        return AdapterTestAction.Result(
            domain=params.label,
            graph={"nodes": [], "edges": []},
        )
