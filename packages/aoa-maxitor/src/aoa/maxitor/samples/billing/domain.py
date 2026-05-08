# packages/aoa-maxitor/src/aoa/maxitor/samples/billing/domain.py
"""Bounded-context marker for payments and settlement."""

from aoa.action_machine.domain import BaseDomain


class BillingDomain(BaseDomain):
    name = "billing"
    description = "Payments, captures, and refunds for the sample storefront"
