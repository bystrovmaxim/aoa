# packages/aoa-demo/src/aoa/demo/model/billing/resources/card_network_gateway.py
"""CardNetworkGateway — the card network a payment's events come from."""

from __future__ import annotations

from aoa.action_machine.intents.entities import entities
from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseGateway, BaseResource
from aoa.demo.model.billing.entities.payment_event_log import PaymentEventLogCoreEntity


@meta(description="Card network gateway (stub)")
@entities(
    PaymentEventLogCoreEntity,
)
class CardNetworkGateway(BaseGateway):
    """Hold the payment events the card network reports; the demo never calls it."""

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        """No wrapper: a nested action may use this resource as it is."""
        return None
