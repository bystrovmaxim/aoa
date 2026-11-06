# packages/aoa-action-machine/src/aoa/action_machine/resources/base_gateway.py
"""
Marker base class for external service gateway resources.

═══════════════════════════════════════════════════════════════════════════════
ROLE
═══════════════════════════════════════════════════════════════════════════════

``BaseGateway`` is the root for resources that delegate work to external
services — payment processors, notification providers, fraud-check APIs,
and any third-party service the process calls but does not own.

The process issues a request and receives a response. It does not know (or
need to know) how the service handles the work internally.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Stripe, SendGrid, Twilio, fraud-check APIs, any external service call.

**Out of scope**
    External data stores you read/write directly (→ ``BaseStorage``).
    Internal engines you create and own (→ ``BaseController``).

═══════════════════════════════════════════════════════════════════════════════
A GATEWAY HAS ITS OWN METHODS
═══════════════════════════════════════════════════════════════════════════════

A gateway is given the service's client when it is built and keeps it private.
Its public methods say what the domain asks of the service, and an aspect calls
them; an aspect never holds the raw client::

    class PaymentGateway(BaseGateway):
        def __init__(self, client: PaymentClient) -> None:
            self._client = client

        async def charge(self, amount: float, currency: str) -> str:
            return await self._client.charge(amount, currency)

A gateway holds no transaction: a nested action gets the same gateway, and a
rollup run refuses it, since a call already made to a service cannot be taken back.
"""

from abc import ABC

from aoa.action_machine.graph.core.exclude_graph_model import exclude_graph_model
from aoa.action_machine.resources.base_data_source import TDataSource_co
from aoa.action_machine.resources.base_resource import BaseResource


@exclude_graph_model
class BaseGateway(BaseResource[TDataSource_co], ABC):
    """
    AI-CORE-BEGIN
        ROLE: Root for resources that delegate work to external services.
        CONTRACT: Do not assume the service retains state between calls.
        INVARIANTS: You do not know how the service works internally.
    AI-CORE-END
    """

    def get_wrapper_class(self) -> type[BaseResource] | None:
        """No wrapper: a gateway holds no transaction, so a nested action gets the same gateway."""
        return None
