# packages/aoa-demo/src/aoa/demo/model/gift_cards/entities/gift_card.py
from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from aoa.action_machine.domain import BaseCoreEntity
from aoa.action_machine.intents.entity import entity
from aoa.demo.model.gift_cards.entities.gift_card_lifecycle import GiftCardLifecycle
from aoa.demo.model.gift_cards.gift_cards_domain import GiftCardsDomain


@entity(description="A gift card a customer bought, with what is left on it", domain=GiftCardsDomain)
class GiftCardCoreEntity(BaseCoreEntity):
    id: str = Field(description="Gift card id")
    lifecycle: GiftCardLifecycle = Field(description="Gift card lifecycle")
    code: str = Field(description="Code printed on the card")
    balance: Decimal = Field(description="Money left on the card", ge=0)


GiftCardCoreEntity.model_rebuild()
