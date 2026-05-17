# packages/aoa-examples/src/aoa/examples/model/catalog_custody/actions/register_snapshot_peek_action.py
"""Read-only custody register snapshot across regulated SKUs."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.examples.model.catalog_custody.catalog_custody_domain import CatalogCustodyDomain
from aoa.examples.model.catalog_custody.catalog_officer_role import CatalogOfficerRole


@meta(
    description="Snapshot peek over regulated SKU custody register (immutable read model slice)",
    domain=CatalogCustodyDomain,
)
@check_roles(CatalogOfficerRole)
class RegisterSnapshotPeekAction(
    BaseAction["RegisterSnapshotPeekAction.Params", "RegisterSnapshotPeekAction.Result"],
):
    class Params(BaseParams):
        custody_scope_token: str = Field(default="", description="Partition key for guarded catalog slice")

    class Result(BaseResult):
        ok: bool = Field(default=True, description="Snapshot materialized acknowledgement")

    @summary_aspect("Register snapshot peek")
    async def register_peek_summary(
        self,
        params: Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> Result:
        _ = (params, state, box, connections)
        return self.Result()
