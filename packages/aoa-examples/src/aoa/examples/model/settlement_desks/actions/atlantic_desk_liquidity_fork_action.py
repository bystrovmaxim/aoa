# packages/aoa-examples/src/aoa/examples/model/settlement_desks/actions/atlantic_desk_liquidity_fork_action.py
"""Atlantic wire desk fork — specialises liquidity sweep posture."""

from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.examples.model.settlement_desks.actions.liquidity_platform_sweep_action import LiquidityPlatformSweepAction
from aoa.examples.model.settlement_desks.arbitration_judge_role import ArbitrationJudgeRole
from aoa.examples.model.settlement_desks.settlement_desks_domain import SettlementDesksDomain


@meta(description="Atlantic venue liquidity fork keyed off chartered sweep posture", domain=SettlementDesksDomain)
@check_roles(ArbitrationJudgeRole)
class AtlanticDeskLiquidityForkAction(LiquidityPlatformSweepAction):
    @summary_aspect("Atlantic liquidity fork")
    async def atlantic_fork_summary(
        self,
        params: LiquidityPlatformSweepAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> LiquidityPlatformSweepAction.Result:
        _ = (params, state, box, connections)
        return self.Result()
