# src/maxitor/test_domain/dependencies/payment.py
"""Заглушка платежа — только для графа @depends."""


class TestPaymentService:
    async def charge(self, amount: float) -> str:
        return "TXN-TEST"

    async def refund(self, txn_id: str) -> None:
        return None
