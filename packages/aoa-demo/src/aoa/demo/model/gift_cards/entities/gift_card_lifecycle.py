# packages/aoa-demo/src/aoa/demo/model/gift_cards/entities/gift_card_lifecycle.py
"""Gift card lifecycle demo."""

from __future__ import annotations

from pydantic import Field

from aoa.action_machine.domain import (
    BaseStateEntity,
    Lifecycle,
    value,
)


class GiftCardStateEntity(BaseStateEntity):
    """Status of the GiftCard axis."""

    sort_order: int = Field(default=0, description="Presentation order")

    ISSUED = value(code="issued", display_name="Issued", sort_order=1)
    ACTIVE = value(code="active", display_name="Active", sort_order=2)
    SPENT = value(code="spent", display_name="Spent", sort_order=3)


class GiftCardLifecycle(Lifecycle[GiftCardStateEntity]):
    """Three states: issued → active → spent."""

    _template = (
        Lifecycle()
        .state(GiftCardStateEntity.ISSUED)
        .to(GiftCardStateEntity.ACTIVE)
        .initial()
        .state(GiftCardStateEntity.ACTIVE)
        .to(GiftCardStateEntity.SPENT)
        .intermediate()
        .state(GiftCardStateEntity.SPENT)
        .final()
    )
