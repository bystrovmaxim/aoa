# packages/aoa-demo/src/aoa/demo/model/gift_cards/gift_cards_domain.py
"""Bounded-context marker for gift cards."""

from aoa.action_machine.domain import BaseDomain


class GiftCardsDomain(BaseDomain):
    name = "gift_cards"
    description = "Gift cards a customer buys and spends against an order"
