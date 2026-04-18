# src/maxitor/samples/billing/actions/credit_memo_preview.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.auth.none_role import NoneRole
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from maxitor.samples.billing.domain import BillingDomain


@meta(description="Preview credit memo totals (billing sample stub)", domain=BillingDomain)
@check_roles(NoneRole)
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
        state: Any,
        box: Any,
        connections: Any,
    ) -> CreditMemoPreviewAction.Result:
        return CreditMemoPreviewAction.Result(preview_id=f"cm-prev-{params.invoice_id}")
