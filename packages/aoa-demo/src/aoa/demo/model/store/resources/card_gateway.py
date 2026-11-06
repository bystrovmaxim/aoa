# packages/aoa-demo/src/aoa/demo/model/store/resources/card_gateway.py
"""StorefrontCardGateway — the card network, as the storefront reaches it."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseGateway, BaseResource
from aoa.demo.model.data_sources.card_network_data_source import CardNetworkDataSource
from aoa.demo.model.store.store_domain import StoreDomain


@meta(description="Card network gateway of the storefront (stub)", domain=StoreDomain)
class StorefrontCardGateway(BaseGateway[CardNetworkDataSource]):
    """
    Authorize a card at checkout; the demo never calls it.

    The card network is one external service of two domains: billing reaches it through
    ``CardNetworkGateway`` for the payment events it reports, the storefront through this
    gateway to authorize a card. Both name ``CardNetworkDataSource``, one resource per domain,
    so the data source alone decides how the service's connection is shared.
    """

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
