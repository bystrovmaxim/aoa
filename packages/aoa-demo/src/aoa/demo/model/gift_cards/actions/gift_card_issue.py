# packages/aoa-demo/src/aoa/demo/model/gift_cards/actions/gift_card_issue.py
from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.gift_cards.gift_card_issuer_role import GiftCardIssuerRole
from aoa.demo.model.gift_cards.gift_cards_domain import GiftCardsDomain


@meta(description="Issue a gift card with a balance (sample stub)", domain=GiftCardsDomain)
@check_roles(GiftCardIssuerRole)
class GiftCardIssueAction(BaseAction["GiftCardIssueAction.Params", "GiftCardIssueAction.Result"]):
    class Params(BaseParams):
        balance: Decimal = Field(description="Money the card starts with", gt=0)

    class Result(BaseResult):
        code: str = Field(description="Code printed on the new card")

    @summary_aspect("Issue card")
    async def issue_summary(
        self,
        params: GiftCardIssueAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> GiftCardIssueAction.Result:
        return GiftCardIssueAction.Result(code=f"GC-{params.balance}")
