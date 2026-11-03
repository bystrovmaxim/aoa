# packages/aoa-demo/src/aoa/demo/model/gift_cards/entities/gift_card_redemption.py
from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import Field

from aoa.action_machine.domain import AssociationOne, BaseCoreEntity, NoInverse
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.gift_cards.entities.gift_card import GiftCardCoreEntity
from aoa.demo.model.gift_cards.gift_cards_domain import GiftCardsDomain
from aoa.demo.model.store.entities.sales_core import SalesOrderCoreEntity


@entity(description="Money taken off a gift card to pay for an order", domain=GiftCardsDomain)
class GiftCardRedemptionCoreEntity(BaseCoreEntity):
    id: str = Field(description="Redemption id")
    amount: Decimal = Field(description="Money taken off the card", gt=0)
    card: Annotated[
        AssociationOne[GiftCardCoreEntity],
        NoInverse(),
    ] = Field(description="Card the money came from")
    order: Annotated[
        AssociationOne[SalesOrderCoreEntity],
        NoInverse(),
    ] = Field(description="Order the money paid for")


GiftCardRedemptionCoreEntity.model_rebuild()
