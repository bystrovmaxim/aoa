# src/maxitor/test_domain/dependencies/notification.py
"""Заглушка уведомлений — для @depends с фабрикой."""


class TestNotificationService:
    def __init__(self, gateway: str = "default") -> None:
        self.gateway = gateway

    async def send(self, message: str) -> None:
        return None
