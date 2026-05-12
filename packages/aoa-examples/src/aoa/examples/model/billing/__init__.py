# packages/aoa-examples/src/aoa/examples/model/billing/__init__.py
"""
Payments context: settlement, ledger, full decorator surface on ``InvoiceSettleAction``.

Layout mirrors ``store``: ``dependencies``, ``resources``, ``plugins``, ``actions``,
entities under ``entities``, ``PaymentGateway`` (also used from ``store``).
"""

from aoa.examples.model.billing.domain import BillingDomain
from aoa.examples.model.billing.entities import PaymentEventLogEntity
from aoa.examples.model.billing.resources.payment_gateway import PaymentGateway

__all__ = ["BillingDomain", "PaymentEventLogEntity", "PaymentGateway"]
