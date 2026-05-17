# packages/aoa-examples/src/aoa/examples/model/catalog_custody/custody_access_steward_role.py
"""CustodyAccessStewardRole — coarse access steward for custody-gated catalogs."""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.intents.check_roles import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class CustodyAccessStewardRole(ApplicationRole, ABC):
    name = "catalog_custody_access_steward"
    description = "Baseline steward that may open custody-gated catalog surfaces"
