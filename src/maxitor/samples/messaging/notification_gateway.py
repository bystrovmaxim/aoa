# src/maxitor/samples/messaging/notification_gateway.py
"""Заглушка канала уведомлений."""

class NotificationGateway:
    def __init__(self, channel: str = "default") -> None:
        self.channel = channel

    async def send(self, message: str) -> None:
        return None
