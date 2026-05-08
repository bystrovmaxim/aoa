# packages/aoa-maxitor/src/aoa/maxitor/samples/billing/actions/dunning_schedule.py
from __future__ import annotations

from typing import Any

from pydantic import Field

from aoa.action_machine.auth import NoneRole
from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult
from aoa.maxitor.samples.billing.domain import BillingDomain


@meta(description="Schedule dunning retries (billing sample stub)", domain=BillingDomain)
@check_roles(NoneRole)
class DunningScheduleAction(
    BaseAction["DunningScheduleAction.Params", "DunningScheduleAction.Result"],
):
    class Params(BaseParams):
        account_id: str = Field(description="Billing account id")

    class Result(BaseResult):
        next_run_iso: str = Field(description="Stub next dunning timestamp")

    @summary_aspect("Schedule")
    async def schedule_summary(
        self,
        params: DunningScheduleAction.Params,
        state: Any,
        box: Any,
        connections: Any,
    ) -> DunningScheduleAction.Result:
        return DunningScheduleAction.Result(next_run_iso=f"2099-01-01T00:00:00Z:{params.account_id}")
