# packages/aoa-maxitor/src/aoa/maxitor/samples/messaging/domain.py
"""Bounded-context marker for customer notifications."""

from aoa.action_machine.domain import BaseDomain


class MessagingDomain(BaseDomain):
    name = "messaging"
    description = "Transactional email/SMS/push stubs for the sample app"
