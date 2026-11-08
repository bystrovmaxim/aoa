# tests/scenarios/domain_model/services.py
"""
Dependency service types for the test domain model.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Clients of external services and the gateways the orders domain reaches them through.
``@depends`` targets are the ``*Gateway`` classes; tests pass ``AsyncMock(spec=Client)``
into ``XGateway(mock)`` and map ``{XGateway: instance}`` on ``TestBench``.

Key rule: every method used by aspects/compensators must be declared on the client and on its gateway,
otherwise spec mocks raise `AttributeError`.

═══════════════════════════════════════════════════════════════════════════════
INTERFACES
═══════════════════════════════════════════════════════════════════════════════

`PaymentClient` (`charge`, `refund`), `NotificationClient` (`send`),
`InventoryClient` (`reserve`, `unreserve`).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    async def charge_aspect(self, params, state, box, connections):
        payment = await box.resolve(PaymentGateway)
        txn_id = await payment.charge(params.amount, params.currency)
        return {"txn_id": txn_id}

    async def rollback_charge_compensate(self, params, state_before,
                                         state_after, box, connections, error):
        payment = await box.resolve(PaymentGateway)
        await payment.refund(state_after["txn_id"])

    async def reserve_aspect(self, params, state, box, connections):
        inventory = await box.resolve(InventoryGateway)
        reservation_id = await inventory.reserve(params.item_id, 1)
        return {"reservation_id": reservation_id}

    # Tests
    mock_payment = AsyncMock(spec=PaymentClient)
    bench = TestBench(mocks={PaymentGateway: PaymentGateway(mock_payment)})

═══════════════════════════════════════════════════════════════════════════════
LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

This module defines only interfaces and intentionally raises
`NotImplementedError`. Behavior lives in mocks/fixtures.

A gateway keeps its client private and has one method per thing the domain asks of the
service: an aspect never holds the raw client.
"""


from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.resources import BaseGateway


class PaymentClient:
    """
    Payment processing service.

    Provides charge() for debits and refund() for refunds. In production
    this would talk to a payment gateway. In tests, use AsyncMock(spec=PaymentClient).

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
        raise NotImplementedError("PaymentClient.charge() is not implemented")

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
        raise NotImplementedError("PaymentClient.refund() is not implemented")


@meta(description="Payment gateway of the orders domain")
class PaymentGateway(BaseGateway):
    """Gateway of the orders domain to the payment provider."""

    def __init__(self, client: PaymentClient) -> None:
        self._client = client

    async def charge(self, amount: float, currency: str) -> str:
        """Charge funds and return the transaction id."""
        return await self._client.charge(amount, currency)

    async def refund(self, txn_id: str) -> bool:
        """Refund a transaction; compensators call it to undo a charge."""
        return await self._client.refund(txn_id)


class NotificationClient:
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
        raise NotImplementedError("NotificationClient.send() is not implemented")


@meta(description="Notification gateway of the orders domain")
class NotificationGateway(BaseGateway):
    """Gateway of the orders domain to the notification service."""

    def __init__(self, client: NotificationClient) -> None:
        self._client = client

    async def send(self, user_id: str, message: str) -> bool:
        """Send a notification to a user."""
        return await self._client.send(user_id, message)


class InventoryClient:
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
        raise NotImplementedError("InventoryClient.reserve() is not implemented")

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
        raise NotImplementedError("InventoryClient.unreserve() is not implemented")


@meta(description="Inventory gateway of the orders domain")
class InventoryGateway(BaseGateway):
    """Gateway of the orders domain to the inventory service."""

    def __init__(self, client: InventoryClient) -> None:
        self._client = client

    async def reserve(self, item_id: str, quantity: int) -> str:
        """Reserve stock and return the reservation id."""
        return await self._client.reserve(item_id, quantity)

    async def unreserve(self, reservation_id: str) -> bool:
        """Cancel a reservation; compensators call it to undo a reserve."""
        return await self._client.unreserve(reservation_id)


def default_payment_gateway() -> PaymentGateway:
    return PaymentGateway(PaymentClient())


def default_notification_gateway() -> NotificationGateway:
    return NotificationGateway(NotificationClient())


def default_inventory_gateway() -> InventoryGateway:
    return InventoryGateway(InventoryClient())
