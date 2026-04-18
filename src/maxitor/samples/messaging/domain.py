# src/maxitor/samples/messaging/domain.py
"""Маркер bounded context «уведомления клиенту»."""

from action_machine.domain.base_domain import BaseDomain


class MessagingDomain(BaseDomain):
    name = "messaging"
    description = "Transactional email/SMS/push stubs for the sample app"
