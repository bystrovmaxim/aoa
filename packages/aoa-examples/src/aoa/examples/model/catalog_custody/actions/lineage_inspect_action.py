# packages/aoa-examples/src/aoa/examples/model/catalog_custody/actions/lineage_inspect_action.py
"""Lineage attestations specialised on snapshot peek spine."""

from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.examples.model.catalog_custody.actions.register_snapshot_peek_action import RegisterSnapshotPeekAction
from aoa.examples.model.catalog_custody.catalog_custody_domain import CatalogCustodyDomain
from aoa.examples.model.catalog_custody.catalog_officer_role import CatalogOfficerRole


@meta(
    description="Lineage attestation review on custody register snapshot peek",
    domain=CatalogCustodyDomain,
)
@check_roles(CatalogOfficerRole)
class LineageInspectAction(RegisterSnapshotPeekAction):
    @summary_aspect("Lineage attest review")
    async def lineage_inspect_summary(
        self,
        params: RegisterSnapshotPeekAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> RegisterSnapshotPeekAction.Result:
        _ = (params, state, box, connections)
        return self.Result()
