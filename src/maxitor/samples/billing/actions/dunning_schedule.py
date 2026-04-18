# src/maxitor/samples/billing/actions/dunning_schedule.py
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


class DunningScheduleParams(BaseParams):
    account_id: str = Field(description="Billing account id")


class DunningScheduleResult(BaseResult):
    next_run_iso: str = Field(description="Stub next dunning timestamp")


@meta(description="Schedule dunning retries (billing sample stub)", domain=BillingDomain)
@check_roles(NoneRole)
class DunningScheduleAction(BaseAction[DunningScheduleParams, DunningScheduleResult]):
    @summary_aspect("Schedule")
    async def schedule_summary(
        self,
        params: DunningScheduleParams,
        state: Any,
        box: Any,
        connections: Any,
    ) -> DunningScheduleResult:
        return DunningScheduleResult(next_run_iso=f"2099-01-01T00:00:00Z:{params.account_id}")
