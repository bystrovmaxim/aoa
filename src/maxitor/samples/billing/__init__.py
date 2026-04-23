# src/maxitor/samples/billing/__init__.py
"""
Платёжный контекст: списания, журнал, полный набор декораторов на действии ``InvoiceSettleAction``.

Структура зеркалит ``store``: ``dependencies``, ``resources``, ``plugins``, ``actions``,
сущности в ``entities``, шлюз ``PaymentGateway`` (также используется ``store``).
"""

from maxitor.samples.billing.domain import BillingDomain
from maxitor.samples.billing.entities import PaymentEventLogEntity
from maxitor.samples.billing.resources.payment_gateway import PaymentGateway

__all__ = ["BillingDomain", "PaymentEventLogEntity", "PaymentGateway"]
