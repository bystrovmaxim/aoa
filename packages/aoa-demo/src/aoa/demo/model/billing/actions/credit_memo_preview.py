# packages/aoa-demo/src/aoa/demo/model/billing/actions/credit_memo_preview.py
from __future__ import annotations

from pydantic import Field

from aoa.action_machine.auth import GuestRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.billing.domain import BillingDomain


@meta(description="Preview credit memo totals (billing sample stub)", domain=BillingDomain)
@check_roles(GuestRole)
class CreditMemoPreviewAction(
    BaseAction["CreditMemoPreviewAction.Params", "CreditMemoPreviewAction.Result"],
):
    class Params(BaseParams):
        invoice_id: str = Field(description="Source invoice id")

    class Result(BaseResult):
        preview_id: str = Field(description="Stub preview id")

    @summary_aspect("Build preview")
    async def preview_summary(
        self,
        params: CreditMemoPreviewAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> CreditMemoPreviewAction.Result:
        return CreditMemoPreviewAction.Result(preview_id=f"cm-prev-{params.invoice_id}")
