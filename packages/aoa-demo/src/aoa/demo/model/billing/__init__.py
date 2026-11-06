# packages/aoa-demo/src/aoa/demo/model/billing/__init__.py
"""
Payments context: settlement, ledger, full decorator surface on ``InvoiceSettleAction``.

Layout mirrors ``store``: ``dependencies``, ``resources``, ``plugins``, ``actions``,
entities under ``entities``, ``PaymentClient`` (also used from ``store``).
"""

from aoa.demo.model.billing.domain import BillingDomain
from aoa.demo.model.billing.entities import PaymentEventLogCoreEntity
from aoa.demo.model.billing.resources.payment_gateway import PaymentClient

__all__ = ["BillingDomain", "PaymentClient", "PaymentEventLogCoreEntity"]
