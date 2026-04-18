# src/maxitor/samples/messaging/dependencies/webhook_fanout.py
"""Фан-аут вебхуков — третья зависимость (как нотификации + SMTP)."""


class WebhookFanoutStub:
    async def post(self, url: str, payload: str) -> int:
        return 202
