# packages/aoa-demo/src/aoa/demo/model/messaging/domain.py
"""Bounded-context marker for customer notifications."""

from aoa.action_machine.domain import BaseDomain


class MessagingDomain(BaseDomain):
    name = "messaging"
    description = "Transactional email/SMS/push stubs for the sample app"
