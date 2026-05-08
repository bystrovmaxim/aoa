# packages/aoa-maxitor/src/aoa/maxitor/samples/messaging/dependencies/__init__.py
from aoa.maxitor.samples.messaging.resources.smtp_transport import SmtpTransportStub
from aoa.maxitor.samples.messaging.resources.webhook_fanout import WebhookFanoutStub

__all__ = ["SmtpTransportStub", "WebhookFanoutStub"]
