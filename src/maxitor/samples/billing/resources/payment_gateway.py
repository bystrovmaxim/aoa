# src/maxitor/samples/billing/resources/payment_gateway.py
"""Заглушка платёжного шлюза для ``@depends`` и ресурсный менеджер для ``connections``."""

from action_machine.intents.meta.meta_decorator import meta
from action_machine.resources.external_service.external_service_resource import (
    ExternalServiceResource,
)
from maxitor.samples.billing.domain import BillingDomain


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
