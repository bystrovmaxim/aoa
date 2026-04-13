# tests/scenarios/domain_model/services.py
"""
Dependency service types for the test domain model.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Service interfaces used by `@depends`. Tests replace implementations with
`AsyncMock(spec=ServiceClass)` and call them via `box.resolve(...)`.

Key rule: every method used by aspects/compensators must be declared here,
otherwise spec mocks raise `AttributeError`.

═══════════════════════════════════════════════════════════════════════════════
INTERFACES
═══════════════════════════════════════════════════════════════════════════════

`PaymentService` (`charge`, `refund`), `NotificationService` (`send`),
`InventoryService` (`reserve`, `unreserve`).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    async def charge_aspect(self, params, state, box, connections):
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, params.currency)
        return {"txn_id": txn_id}

    async def rollback_charge_compensate(self, params, state_before,
                                         state_after, box, connections, error):
        payment = box.resolve(PaymentService)
        await payment.refund(state_after["txn_id"])

    async def reserve_aspect(self, params, state, box, connections):
        inventory = box.resolve(InventoryService)
        reservation_id = await inventory.reserve(params.item_id, 1)
        return {"reservation_id": reservation_id}

    # Tests
    mock_payment = AsyncMock(spec=PaymentService)
    bench = TestBench(mocks={PaymentService: mock_payment})

═══════════════════════════════════════════════════════════════════════════════
LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

This module defines only interfaces and intentionally raises
`NotImplementedError`. Behavior lives in mocks/fixtures.
"""


class PaymentService:
    """
    Payment processing service.

    Provides charge() for debits and refund() for refunds. In production
    this would talk to a payment gateway. In tests, use AsyncMock(spec=PaymentService).

    refund() is used by @compensate handlers to undo a successful charge
    when a later aspect fails.
    """

    async def charge(self, amount: float, currency: str) -> str:
        """
        Charge funds and return a transaction id.

        Args:
            amount: amount to charge.
            currency: ISO 4217 code (e.g. "RUB", "USD").

        Returns:
            Unique transaction identifier.
        """
        raise NotImplementedError("PaymentService.charge() is not implemented")

    async def refund(self, txn_id: str) -> bool:
        """
        Refund a transaction by id.

        Called by compensators during Saga rollback after a successful charge()
        when a later aspect fails. ActionProductMachine unwinds the compensation
        stack and calls refund() to reverse the charge.

        Args:
            txn_id: transaction id from charge().

        Returns:
            True if the refund succeeded.
        """
        raise NotImplementedError("PaymentService.refund() is not implemented")


class NotificationService:
    """
    Notification service.

    Provides send() for user messages. In production: email/SMS/push.
    In tests: AsyncMock.
    """

    async def send(self, user_id: str, message: str) -> bool:
        """
        Send a notification to a user.

        Args:
            user_id: recipient id.
            message: message body.

        Returns:
            True if the send succeeded.
        """
        raise NotImplementedError("NotificationService.send() is not implemented")


class InventoryService:
    """
    Inventory / stock service.

    Provides reserve() and unreserve(). Used by compensating Actions
    (CompensatedOrderAction, CompensateAndOnErrorAction, etc.).

    unreserve() is called by compensators when rolling back a reservation.
    """

    async def reserve(self, item_id: str, quantity: int) -> str:
        """
        Reserve stock for an item.

        Args:
            item_id: product id.
            quantity: units to reserve.

        Returns:
            Unique reservation identifier.
        """
        raise NotImplementedError("InventoryService.reserve() is not implemented")

    async def unreserve(self, reservation_id: str) -> bool:
        """
        Cancel a reservation.

        Called by compensators during rollback after a successful reserve()
        when a later aspect fails.

        Args:
            reservation_id: id returned by reserve().

        Returns:
            True if unreserve succeeded.
        """
        raise NotImplementedError("InventoryService.unreserve() is not implemented")
