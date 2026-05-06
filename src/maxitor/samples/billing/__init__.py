# src/maxitor/samples/billing/__init__.py
"""
Payments context: settlement, ledger, full decorator surface on ``InvoiceSettleAction``.

Layout mirrors ``store``: ``dependencies``, ``resources``, ``plugins``, ``actions``,
entities under ``entities``, ``PaymentGateway`` (also used from ``store``).
"""

from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities import PaymentEventLogEntity
from maxitor.samples.billing.resources.payment_gateway import PaymentGateway

__all__ = ["BillingDomain", "PaymentEventLogEntity", "PaymentGateway"]
