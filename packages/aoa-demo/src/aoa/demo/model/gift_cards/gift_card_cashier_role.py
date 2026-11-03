# packages/aoa-demo/src/aoa/demo/model/gift_cards/gift_card_cashier_role.py
"""GiftCardCashierRole — takes gift cards as payment."""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.intents.check_roles import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class GiftCardCashierRole(ApplicationRole, ABC):
    name = "gift_card_cashier"
    description = "Redeems gift cards against an order"
