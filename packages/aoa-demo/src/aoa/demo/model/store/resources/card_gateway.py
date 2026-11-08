# packages/aoa-demo/src/aoa/demo/model/store/resources/card_gateway.py
"""StorefrontCardGateway — the card network, as the storefront reaches it."""

from __future__ import annotations

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseGateway, BaseResource


@meta(description="Card network gateway of the storefront (stub)")
class StorefrontCardGateway(BaseGateway):
    """
    Authorize a card at checkout; the demo never calls it.

    The card network is one external service of two domains: billing reaches it through
    ``CardNetworkGateway`` for the payment events it reports, the storefront through this
    gateway to authorize a card — one resource per domain.
    """

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
