# packages/aoa-maxitor/src/aoa/maxitor/samples/billing/resources/payment_gateway.py
"""Payment-gateway stub for ``@depends`` and ``connections`` resource manager."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources.external_service import ExternalServiceResource
from aoa.maxitor.samples.billing.domain import BillingDomain


class PaymentGateway:
    async def charge(self, amount: float) -> str:
        return "TXN-SAMPLE"

    async def refund(self, txn_id: str) -> None:
        return None


@meta(
    description="Payment gateway client for aspects/connections (stub)",
    domain=BillingDomain,
)
class PaymentGatewayResource(ExternalServiceResource[PaymentGateway]):
    pass
