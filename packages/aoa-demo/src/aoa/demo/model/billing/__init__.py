# packages/aoa-demo/src/aoa/demo/model/billing/__init__.py
"""
Payments context: settlement, ledger, full decorator surface on ``InvoiceSettleAction``.

Layout mirrors ``store``: ``dependencies``, ``resources``, ``plugins``, ``actions``,
entities under ``entities``, ``PaymentGateway`` (also used from ``store``).
"""

from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities import PaymentEventLogEntity
from aoa.demo.model.billing.resources.payment_gateway import PaymentGateway

__all__ = ["BillingDomain", "PaymentEventLogEntity", "PaymentGateway"]
