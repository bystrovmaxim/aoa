# packages/aoa-demo/src/aoa/demo/model/actions/get_example_model_graph_json_action.py
"""
GetExampleModelGraphJsonAction — return registered demo coordinator interchange JSON.
"""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.graph_json_domain import ExampleModelGraphJsonDomain
from aoa.demo.model.services.graph_json_service import ExampleModelGraphJsonService


@meta(
    description="Return interchange JSON for the example-registered NodeGraphCoordinator.",
    domain=ExampleModelGraphJsonDomain,
)
@check_roles(GuestRole)
class GetExampleModelGraphJsonAction(
    BaseAction["GetExampleModelGraphJsonAction.Params", "GetExampleModelGraphJsonAction.Result"]
):
    class Params(BaseParams):
        """No query or body parameters."""

    class Result(BaseResult):
        coordinator_json: str = Field(
            description="Interchange export from NodeGraphCoordinator.to_json().",
        )

    @summary_aspect("Serialize demo coordinator to interchange JSON")
    async def export_coordinator_json_summary(
        self,
        params: GetExampleModelGraphJsonAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GetExampleModelGraphJsonAction.Result:
        raw = ExampleModelGraphJsonService().coordinator_json()
        return GetExampleModelGraphJsonAction.Result(coordinator_json=raw)
