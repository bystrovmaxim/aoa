# packages/aoa-demo/src/aoa/demo/model/data_sources/notification_gateway_data_source.py
"""NotificationGatewayDataSource — the notification service."""

from aoa.action_machine.intents.meta import meta
from aoa.action_machine.resources import ExternalServiceDataSource


@meta(description="The notification service")
class NotificationGatewayDataSource(ExternalServiceDataSource):
    """A demo external service: the gateway notifications go out through."""
