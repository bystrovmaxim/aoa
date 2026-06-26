# packages/aoa-demo/src/aoa/demo/model/messaging/dependencies/__init__.py
from aoa.demo.model.messaging.resources.smtp_transport import SmtpTransportStub
from aoa.demo.model.messaging.resources.webhook_fanout import WebhookFanoutStub

__all__ = ["SmtpTransportStub", "WebhookFanoutStub"]
