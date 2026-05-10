# tests/action_machine/adapters/json_schema_adapter_fixtures.py
"""
Shared Action + JsonSchemaValue types for adapter PR-2 tests.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Single minimal action used by FastAPI and MCP adapter tests to assert OpenAPI,
HTTP JSON bodies, MCP tool schemas, and result serialization with a
schema-backed ``graph`` field.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import NoneRole, check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.model.json_schema_value import JsonSchemaValue
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from tests.action_machine.scenarios.domain_model.domains import TestDomain

_EMPTY_GRAPH_VERTEX: dict[str, Any] = {"type": "object", "properties": {}, "additionalProperties": False}
GRAPH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "nodes": {"type": "array", "items": _EMPTY_GRAPH_VERTEX},
        "edges": {"type": "array", "items": _EMPTY_GRAPH_VERTEX},
    },
    "required": ["nodes", "edges"],
    "additionalProperties": False,
}
GraphJson = JsonSchemaValue.define(name="GraphJson", schema=GRAPH_SCHEMA)


@meta(description="Adapter test action for JsonSchemaValue transport checks", domain=TestDomain)
@check_roles(NoneRole)
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
        params: Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Result:
        return AdapterTestAction.Result(
            domain=params.label,
            graph={"nodes": [], "edges": []},
        )
