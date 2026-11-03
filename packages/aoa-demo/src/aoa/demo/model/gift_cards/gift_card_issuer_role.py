# packages/aoa-demo/src/aoa/demo/model/gift_cards/gift_card_issuer_role.py
"""GiftCardIssuerRole — issues gift cards to customers."""

from __future__ import annotations

from abc import ABC

from aoa.action_machine.auth import ApplicationRole
from aoa.action_machine.intents.check_roles import RoleMode, role_mode


@role_mode(RoleMode.ALIVE)
class GiftCardIssuerRole(ApplicationRole, ABC):
    name = "gift_card_issuer"
    description = "Issues gift cards and sets their balance"
