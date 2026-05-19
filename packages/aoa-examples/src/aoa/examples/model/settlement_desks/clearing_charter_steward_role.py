# packages/aoa-examples/src/aoa/examples/model/settlement_desks/clearing_charter_steward_role.py
"""ClearingCharterStewardRole — mandates shared across settlement desks."""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.intents.check_roles import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class ClearingCharterStewardRole(ApplicationRole, ABC):
    name = "clearing_charter_steward"
    description = "Owns netting policies that both venue desks must honour"
