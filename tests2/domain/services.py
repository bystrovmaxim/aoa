# tests2/domain/services.py
"""
Сервисы-зависимости тестовой доменной модели.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Определяет классы сервисов, которые Action объявляют как зависимости
через декоратор @depends. В тестах реальные экземпляры этих классов
заменяются моками (AsyncMock) через TestBench.with_mocks() или
через фикстуры в conftest.py.

Сервисы определяют интерфейс — набор async-методов, которые аспекты
вызывают через box.resolve(PaymentService). В production сервисы
содержат реальную логику; в тестах — подменяются моками.

═══════════════════════════════════════════════════════════════════════════════
СЕРВИСЫ
═══════════════════════════════════════════════════════════════════════════════

- PaymentService — сервис обработки платежей. Метод charge() списывает
  средства и возвращает ID транзакции. Используется в FullAction.

- NotificationService — сервис отправки уведомлений. Метод send()
  отправляет уведомление пользователю. Используется в FullAction.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ACTION
═══════════════════════════════════════════════════════════════════════════════

    @depends(PaymentService, description="Сервис обработки платежей")
    @depends(NotificationService, description="Сервис уведомлений")
    class FullAction(BaseAction[...]): ...

    # В аспекте:
    async def process_payment(self, params, state, box, connections):
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, params.currency)
        return {"txn_id": txn_id}

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

    from unittest.mock import AsyncMock

    mock_payment = AsyncMock(spec=PaymentService)
    mock_payment.charge.return_value = "TXN-TEST-001"

    bench = TestBench(mocks={PaymentService: mock_payment})
    result = await bench.run(FullAction(), params, rollup=False)
"""


class PaymentService:
    """
    Сервис обработки платежей.

    Предоставляет метод charge() для списания средств. В production
    подключается к платёжному шлюзу. В тестах подменяется AsyncMock.
    """

    async def charge(self, amount: float, currency: str) -> str:
        """
        Списывает средства и возвращает ID транзакции.

        Аргументы:
            amount: сумма списания.
            currency: код валюты ISO 4217 (например, "RUB", "USD").

        Возвращает:
            str — уникальный идентификатор транзакции.
        """
        raise NotImplementedError("PaymentService.charge() не реализован")


class NotificationService:
    """
    Сервис отправки уведомлений.

    Предоставляет метод send() для отправки уведомлений пользователям.
    В production отправляет email/SMS/push. В тестах подменяется AsyncMock.
    """

    async def send(self, user_id: str, message: str) -> bool:
        """
        Отправляет уведомление пользователю.

        Аргументы:
            user_id: идентификатор получателя.
            message: текст уведомления.

        Возвращает:
            bool — True если уведомление отправлено успешно.
        """
        raise NotImplementedError("NotificationService.send() не реализован")
