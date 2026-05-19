# packages/aoa-examples/src/aoa/examples/model/settlement_desks/regional_desk_lead_role.py
"""RegionalDeskLeadRole — regional venue desk execution lead."""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.intents.check_roles import RoleMode, role_mode
from aoa.examples.model.settlement_desks.clearing_charter_steward_role import ClearingCharterStewardRole


@role_mode(RoleMode.ALIVE)
class RegionalDeskLeadRole(ClearingCharterStewardRole, ABC):
    name = "regional_clearing_desk_lead"
    description = "Operational lead for mirrored settlement venue executions"
