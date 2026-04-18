# src/maxitor/samples/messaging/dependencies/smtp.py
"""Транспорт «SMTP» — вторая зависимость для домена messaging."""


class SmtpTransportStub:
    async def send_raw(self, to: str, body: str) -> str:
        return "MSG-ID-SMTP-STUB"
