# src/maxitor/samples/messaging/dependencies/__init__.py
from maxitor.samples.messaging.dependencies.smtp import SmtpTransportStub
from maxitor.samples.messaging.dependencies.webhook_fanout import WebhookFanoutStub

__all__ = ["SmtpTransportStub", "WebhookFanoutStub"]
