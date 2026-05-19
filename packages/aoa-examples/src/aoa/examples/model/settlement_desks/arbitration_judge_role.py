# packages/aoa-examples/src/aoa/examples/model/settlement_desks/arbitration_judge_role.py
"""ArbitrationJudgeRole — central arbitrator supervising desk reconciliations."""

from __future__ import annotations

from aoa.action_machine.intents.check_roles import RoleMode, role_mode
from aoa.examples.model.settlement_desks.regional_desk_lead_role import RegionalDeskLeadRole


@role_mode(RoleMode.ALIVE)
class ArbitrationJudgeRole(RegionalDeskLeadRole):
    name = "settlement_arbitration_judge"
    description = "Final authority on bridging disputes exposed by dual-desk merges"
