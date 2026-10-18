# packages/aoa-demo/src/aoa/demo/model/settlement_desks/actions/bi_desk_liquidity_bridge_action.py
"""Bi-desk bridge — mandatory Atlantic fork, optional Pacific extension."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.depends import UseCase, depends
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.settlement_desks.actions.atlantic_desk_liquidity_fork_action import (
    AtlanticDeskLiquidityForkAction,
)
from aoa.demo.model.settlement_desks.actions.pacific_desk_liquidity_fork_action import (
    PacificDeskLiquidityForkAction,
)
from aoa.demo.model.settlement_desks.arbitration_judge_role import ArbitrationJudgeRole
from aoa.demo.model.settlement_desks.settlement_desks_domain import SettlementDesksDomain


@meta(
    description="Desk bridge reconciliations tying mandatory Atlantic merges to Pacific overlays",
    domain=SettlementDesksDomain,
)
@check_roles(ArbitrationJudgeRole)
@depends(
    AtlanticDeskLiquidityForkAction,
    mode=UseCase.include,
    description="Atlantic desk fork is inlined for bridge custody",
)
@depends(
    PacificDeskLiquidityForkAction,
    mode=UseCase.extend,
    description="Pacific overlays remain optional overlays on the chartered bridge",
)
class BiDeskLiquidityBridgeAction(
    BaseAction["BiDeskLiquidityBridgeAction.Params", "BiDeskLiquidityBridgeAction.Result"],
):
    class Params(BaseParams):
        netting_batch: str = Field(default="", description="Cross-desk netting batch token")

    class Result(BaseResult):
        stitched: bool = Field(default=False, description="Bridge stitching acknowledgement")

    @summary_aspect("Bi-desk bridge merge")
    async def bridge_summary(self, params: Params, state: BaseState, box: ToolsBox, connections: dict[str, BaseResource]) -> Result:
        _ = (params, state, box, connections)
        await box.run(AtlanticDeskLiquidityForkAction, AtlanticDeskLiquidityForkAction.Params())
        return self.Result()
