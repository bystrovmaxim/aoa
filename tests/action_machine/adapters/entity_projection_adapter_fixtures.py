# tests/action_machine/adapters/entity_projection_adapter_fixtures.py
"""
Shared Action for adapter tests that use ``BaseEntity.schema()`` wire projections.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Minimal actions whose ``Result`` and/or ``Params`` carry a partial JSON projection of
``SampleEntity`` so MCP adapter tests can assert ``inputSchema`` and serialization
without new production actions.
"""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from tests.action_machine.scenarios.domain_model.domains import TestDomain
from tests.action_machine.scenarios.domain_model.entities import SampleEntity

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
