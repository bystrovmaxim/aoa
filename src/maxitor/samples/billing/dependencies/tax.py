# src/maxitor/samples/billing/dependencies/tax.py
"""Заглушка налогового/прайсинга для второго ``@depends`` в billing."""


class TaxQuoteService:
    async def rate_for(self, jurisdiction: str) -> float:
        return 0.2
