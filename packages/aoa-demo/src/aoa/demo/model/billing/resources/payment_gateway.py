# packages/aoa-demo/src/aoa/demo/model/billing/resources/payment_gateway.py
"""Payment provider: a stub client and the gateway the domain reaches it through."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import BaseGateway
from aoa.demo.model.billing.domain import BillingDomain


class PaymentClient:
    async def charge(self, amount: float) -> str:
        return "TXN-SAMPLE"

    async def refund(self, txn_id: str) -> None:
        return None


@meta(
    description="Payment provider gateway (stub)",
    domain=BillingDomain,
)
class PaymentGateway(BaseGateway):
    """The gateway to the payment provider: its methods are what the domain asks of it."""

    def __init__(self, client: PaymentClient) -> None:
        self._client = client

    async def charge(self, amount: float) -> str:
        """Charge an amount and return the transaction id."""
        return await self._client.charge(amount)

    async def refund(self, txn_id: str) -> None:
        """Refund a captured transaction."""
        return await self._client.refund(txn_id)
