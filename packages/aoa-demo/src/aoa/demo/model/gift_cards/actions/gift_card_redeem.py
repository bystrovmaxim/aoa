# packages/aoa-demo/src/aoa/demo/model/gift_cards/actions/gift_card_redeem.py
from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from aoa.action_machine.intents.aspects import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.model import BaseAction, BaseParams, BaseResult, BaseState
from aoa.action_machine.resources import Connections
from aoa.action_machine.runtime.tools_box import ToolsBox
from aoa.demo.model.gift_cards.gift_card_cashier_role import GiftCardCashierRole
from aoa.demo.model.gift_cards.gift_cards_domain import GiftCardsDomain


@meta(description="Pay part of an order with a gift card (sample stub)", domain=GiftCardsDomain)
@check_roles(GiftCardCashierRole)
class GiftCardRedeemAction(BaseAction["GiftCardRedeemAction.Params", "GiftCardRedeemAction.Result"]):
    class Params(BaseParams):
        code: str = Field(description="Code printed on the card")
        order_id: str = Field(description="Order to pay for")
        amount: Decimal = Field(description="Money to take off the card", gt=0)

    class Result(BaseResult):
        redemption_id: str = Field(description="Id of the redemption")

    @summary_aspect("Redeem card")
    async def redeem_summary(
        self,
        params: GiftCardRedeemAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> GiftCardRedeemAction.Result:
        return GiftCardRedeemAction.Result(redemption_id=f"{params.code}:{params.order_id}")
