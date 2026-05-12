# packages/aoa-examples/src/aoa/examples/model/messaging/dependencies/__init__.py
from aoa.examples.model.messaging.resources.smtp_transport import SmtpTransportStub
from aoa.examples.model.messaging.resources.webhook_fanout import WebhookFanoutStub

__all__ = ["SmtpTransportStub", "WebhookFanoutStub"]
