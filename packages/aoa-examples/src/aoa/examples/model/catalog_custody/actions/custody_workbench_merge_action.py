# packages/aoa-examples/src/aoa/examples/model/catalog_custody/actions/custody_workbench_merge_action.py
"""Workbench merge orchestrator — include lineage attest, extend posting pulse."""

from __future__ import annotations

from typing import Any

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.depends import UseCase, depends
from aoa.action_machine.intents.meta import meta
from aoa.examples.model.catalog_custody.actions.ledger_posting_pulse_action import LedgerPostingPulseAction
from aoa.examples.model.catalog_custody.actions.lineage_inspect_action import LineageInspectAction
from aoa.examples.model.catalog_custody.actions.register_snapshot_peek_action import RegisterSnapshotPeekAction
from aoa.examples.model.catalog_custody.catalog_custody_domain import CatalogCustodyDomain
from aoa.examples.model.catalog_custody.catalog_officer_role import CatalogOfficerRole


@meta(
    description="Custody reconciliation workbench merges peek spine with attest include + postings extend",
    domain=CatalogCustodyDomain,
)
@check_roles(CatalogOfficerRole)
@depends(
    LineageInspectAction,
    mode=UseCase.include,
    description="Lineage attest path is always materialised in the reconciliation merge",
)
@depends(
    LedgerPostingPulseAction,
    mode=UseCase.extend,
    description="Optional postings pulse façade extends custody merge behaviour",
)
class CustodyWorkbenchMergeAction(RegisterSnapshotPeekAction):
    @summary_aspect("Custody reconciliation merge")
    async def reconciliation_merge_summary(
        self,
        params: RegisterSnapshotPeekAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> RegisterSnapshotPeekAction.Result:
        _ = (params, state, box, connections)
        await box.run(LineageInspectAction, LineageInspectAction.Params())
        return self.Result()
