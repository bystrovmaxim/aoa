# src/maxitor/samples/billing/payment_gateway.py
"""Заглушка платёжного шлюза — для графа ``@depends`` и сценариев Saga."""

class PaymentGateway:
    async def charge(self, amount: float) -> str:
        return "TXN-SAMPLE"

    async def refund(self, txn_id: str) -> None:
        return None
