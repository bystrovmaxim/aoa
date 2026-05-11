# packages/aoa-maxitor/src/aoa/maxitor/model/diagrams/actions/get_interchange_graph_payload_action.py
"""
GetInterchangeGraphPayloadAction — interchange graph as JSON for the React G6 viewer.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Emit the same structure the former standalone HTML page embedded: ``nodes``, ``edges``,
``legend_items``, ``node_type_map``, ``bubble_plugins``, and ``constants``.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import ConfigDict, Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.maxitor.model.core.resources.service_graph_resource import (
    SERVICE_GRAPH_CONNECTION_KEY,
    ServiceGraphResource,
)
from aoa.maxitor.model.diagrams.actions.build_interchange_graph_data_action import (
    dag_cycle_violation_keys_from_coordinator,
    interchange_g6_payload_from_nx,
)
from aoa.maxitor.model.diagrams.diagrams_domain import DiagramsDomain
from aoa.maxitor.model.diagrams.interchange_nx_coordinator import node_graph_coordinator_from_interchange_nx


@meta(
    description="Get interchange graph JSON for the Maxitor React G6 viewer (diagrams)",
    domain=DiagramsDomain,
)
@check_roles(NoneRole)
@connection(ServiceGraphResource, key=SERVICE_GRAPH_CONNECTION_KEY, description="Interchange nx graph from LoadGraphAction")
class GetInterchangeGraphPayloadAction(
    BaseAction["GetInterchangeGraphPayloadAction.Params", "GetInterchangeGraphPayloadAction.Result"],
):
    """
    AI-CORE-BEGIN
    ROLE: Emit G6-oriented interchange graph JSON for client rendering.
    CONTRACT: Reads the DiGraph only via ``connections["ServiceGraph"].service``.
    OUTPUT: Dict suitable for AntV G6 ``data`` plus legend and bubble plugins.
    AI-CORE-END
    """

    class Params(BaseParams):
        model_config = ConfigDict(arbitrary_types_allowed=True)

    class Result(BaseResult):
        payload: dict[str, Any] = Field(
            description="G6 graph payload: title, nodes, edges, legend_items, node_type_map, bubble_plugins, constants",
        )

        model_config = ConfigDict(arbitrary_types_allowed=True)

    @summary_aspect("Build interchange graph JSON for the React viewer")
    async def build_graph_payload_summary(
        self,
        params: GetInterchangeGraphPayloadAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GetInterchangeGraphPayloadAction.Result:
        nx_resource = cast(ServiceGraphResource, connections[SERVICE_GRAPH_CONNECTION_KEY])
        coordinator = node_graph_coordinator_from_interchange_nx(nx_resource.service)
        keys = dag_cycle_violation_keys_from_coordinator(coordinator)
        payload = interchange_g6_payload_from_nx(
            nx_resource.service,
            title="Interchange graph",
            cycle_violation_keys=keys,
        )
        return GetInterchangeGraphPayloadAction.Result(payload=payload)
