# packages/aoa-demo/src/aoa/demo/model/billing/resources/card_network_gateway.py
"""CardNetworkGateway — the card network a payment's events come from."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.base_gateway import BaseGateway
from aoa.demo.model.billing.domain import BillingDomain


@meta(description="Card network gateway (stub)", domain=BillingDomain)
class CardNetworkGateway(BaseGateway):
    """Hold the payment events the card network reports; the demo never calls it."""
