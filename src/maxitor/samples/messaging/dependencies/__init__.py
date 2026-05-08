# src/maxitor/samples/messaging/dependencies/__init__.py
from maxitor.samples.messaging.resources.smtp_transport import SmtpTransportStub
from maxitor.samples.messaging.resources.webhook_fanout import WebhookFanoutStub

__all__ = ["SmtpTransportStub", "WebhookFanoutStub"]
