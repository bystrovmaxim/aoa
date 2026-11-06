# packages/aoa-demo/src/aoa/demo/model/billing/resources/card_network_gateway.py
"""CardNetworkGateway — the card network a payment's events come from."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseGateway, BaseResource
from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.data_sources.card_network_data_source import CardNetworkDataSource


@meta(description="Card network gateway (stub)", domain=BillingDomain)
class CardNetworkGateway(BaseGateway[CardNetworkDataSource]):
    """Hold the payment events the card network reports; the demo never calls it."""

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
