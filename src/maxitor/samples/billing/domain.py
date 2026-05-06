# src/maxitor/samples/billing/domain.py
"""Маркер bounded context «платежи и списания»."""

from action_machine.domain import BaseDomain


class BillingDomain(BaseDomain):
    name = "billing"
    description = "Payments, captures, and refunds for the sample storefront"
