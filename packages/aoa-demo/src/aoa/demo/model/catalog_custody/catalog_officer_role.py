# packages/aoa-demo/src/aoa/demo/model/catalog_custody/catalog_officer_role.py
"""CatalogOfficerRole — delegated catalog custody officer."""

from __future__ import annotations

from aoa.action_machine.intents.check_roles import RoleMode, role_mode
from aoa.demo.model.catalog_custody.custody_access_steward_role import CustodyAccessStewardRole


@role_mode(RoleMode.ALIVE)
class CatalogOfficerRole(CustodyAccessStewardRole):
    name = "catalog_custody_officer"
    description = "Officer authorized to attest lineage rows and reconcile posting deltas"
