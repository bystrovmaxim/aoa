# tests/domain/services.py
"""
Сервисы-зависимости тестовой доменной модели.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Определяет классы сервисов, которые Action объявляют как зависимости
через декоратор @depends. В тестах реальные экземпляры этих классов
заменяются моками (AsyncMock) через TestBench или через фикстуры
в conftest.py.

Сервисы определяют интерфейс — набор async-методов, которые аспекты
вызывают через box.resolve(ServiceClass). В production сервисы
содержат реальную логику; в тестах — подменяются моками.

AsyncMock(spec=ServiceClass) строго ограничивает доступные атрибуты
мока теми, что определены в классе. Поэтому КАЖДЫЙ метод, который
вызывается в аспектах или компенсаторах, ОБЯЗАН быть объявлен
в классе сервиса — иначе мок с spec бросит AttributeError.

═══════════════════════════════════════════════════════════════════════════════
СЕРВИСЫ
═══════════════════════════════════════════════════════════════════════════════

- PaymentService — сервис обработки платежей.
  charge() — списание средств, возвращает ID транзакции.
  refund() — возврат средств по ID транзакции (используется
  компенсаторами при откате платежа).
  Используется в FullAction и компенсируемых действиях
  (CompensatedOrderAction, CompensateAndOnErrorAction и др.).

- NotificationService — сервис отправки уведомлений.
  send() — отправка уведомления пользователю.
  Используется в FullAction.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ACTION
═══════════════════════════════════════════════════════════════════════════════

    # В аспекте — списание:
    async def charge_aspect(self, params, state, box, connections):
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, params.currency)
        return {"txn_id": txn_id}

    # В компенсаторе — возврат:
    async def rollback_charge_compensate(self, params, state_before,
                                         state_after, box, connections, error):
        payment = box.resolve(PaymentService)
        await payment.refund(state_after["txn_id"])

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

    from unittest.mock import AsyncMock

    mock_payment = AsyncMock(spec=PaymentService)
    mock_payment.charge.return_value = "TXN-TEST-001"
    mock_payment.refund.return_value = True

    bench = TestBench(mocks={PaymentService: mock_payment})
    result = await bench.run(FullAction(), params, rollup=False)
"""


class PaymentService:
    """
    Сервис обработки платежей.

    Предоставляет методы charge() для списания средств и refund()
    для возврата. В production подключается к платёжному шлюзу.
    В тестах подменяется AsyncMock(spec=PaymentService).

    Метод refund() используется компенсаторами (@compensate) для
    отката платежа при возникновении ошибки в конвейере аспектов.
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

    async def refund(self, txn_id: str) -> bool:
        """
        Выполняет возврат средств по ID транзакции.

        Вызывается компенсатором при откате платежа в паттерне Saga.
        При ошибке в любом аспекте после успешного charge()
        ActionProductMachine разматывает стек компенсации и вызывает
        refund() для отмены списания.

        Аргументы:
            txn_id: идентификатор транзакции, полученный от charge().

        Возвращает:
            bool — True если возврат выполнен успешно.
        """
        raise NotImplementedError("PaymentService.refund() не реализован")


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
