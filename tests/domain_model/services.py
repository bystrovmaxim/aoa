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

- NotificationService — сервис отправки уведомлений.
  send() — отправка уведомления пользователю.

- InventoryService — сервис управления запасами.
  reserve() — резервирование товара, возвращает ID резервации.
  unreserve() — отмена резервации (используется компенсаторами).

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

    # В аспекте — резервирование:
    async def reserve_aspect(self, params, state, box, connections):
        inventory = box.resolve(InventoryService)
        reservation_id = await inventory.reserve(params.item_id, 1)
        return {"reservation_id": reservation_id}

    # В компенсаторе — отмена резервирования:
    async def rollback_reserve_compensate(self, params, state_before,
                                          state_after, box, connections, error):
        inventory = box.resolve(InventoryService)
        await inventory.unreserve(state_after["reservation_id"])

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

    from unittest.mock import AsyncMock

    mock_payment = AsyncMock(spec=PaymentService)
    mock_payment.charge.return_value = "TXN-TEST-001"
    mock_payment.refund.return_value = True

    mock_inventory = AsyncMock(spec=InventoryService)
    mock_inventory.reserve.return_value = "RES-TEST-001"
    mock_inventory.unreserve.return_value = True

    bench = TestBench(mocks={PaymentService: mock_payment, InventoryService: mock_inventory})
    result = await bench.run(Action(), params, rollup=False)
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


class InventoryService:
    """
    Сервис управления запасами.

    Предоставляет методы reserve() для резервирования товара и unreserve()
    для отмены резервации. Используется в компенсируемых действиях
    (CompensatedOrderAction, CompensateAndOnErrorAction и др.).

    Метод unreserve() вызывается компенсатором при откате резервирования
    в паттерне Saga.
    """

    async def reserve(self, item_id: str, quantity: int) -> str:
        """
        Резервирует товар на складе.

        Аргументы:
            item_id: идентификатор товара.
            quantity: количество для резервирования.

        Возвращает:
            str — уникальный идентификатор резервации.
        """
        raise NotImplementedError("InventoryService.reserve() не реализован")

    async def unreserve(self, reservation_id: str) -> bool:
        """
        Отменяет резервацию товара.

        Вызывается компенсатором при откате резервирования.
        При ошибке в любом аспекте после успешного reserve()
        ActionProductMachine разматывает стек компенсации и вызывает
        unreserve() для отмены резервации.

        Аргументы:
            reservation_id: идентификатор резервации, полученный от reserve().

        Возвращает:
            bool — True если отмена выполнена успешно.
        """
        raise NotImplementedError("InventoryService.unreserve() не реализован")
