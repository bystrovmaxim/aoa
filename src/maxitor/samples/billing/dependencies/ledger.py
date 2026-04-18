# src/maxitor/samples/billing/dependencies/ledger.py
"""Заглушка бухгалтерского журнала для рёбер ``@depends`` в домене billing."""


class LedgerArchiveService:
    async def append(self, event_type: str, payload: str) -> str:
        return "LEDGER-ROW-1"
