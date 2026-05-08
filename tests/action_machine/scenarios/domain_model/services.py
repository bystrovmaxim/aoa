# tests/scenarios/domain_model/services.py
"""
Dependency service types for the test domain model.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Service interfaces used as ``.service`` clients. ``@depends`` targets are
``*Resource`` wrappers; tests pass ``AsyncMock(spec=Client)`` into
``ResourceClass(mock)`` and map ``{ResourceClass: instance}`` on ``TestBench``.

Key rule: every method used by aspects/compensators must be declared here,
otherwise spec mocks raise `AttributeError`.

═══════════════════════════════════════════════════════════════════════════════
INTERFACES
═══════════════════════════════════════════════════════════════════════════════

`PaymentService` (`charge`, `refund`), `NotificationService` (`send`),
`InventoryService` (`reserve`, `unreserve`), `SagaCompensateTraceService`
(test-only hook for asserting compensator calls).

═══════════════════════════════════════════════════════════════════════════════
EXAMPLE
═══════════════════════════════════════════════════════════════════════════════

    async def charge_aspect(self, params, state, box, connections):
        payment = box.resolve(PaymentServiceResource).service
        txn_id = await payment.charge(params.amount, params.currency)
        return {"txn_id": txn_id}

    async def rollback_charge_compensate(self, params, state_before,
                                         state_after, box, connections, error):
        payment = box.resolve(PaymentServiceResource).service
        await payment.refund(state_after["txn_id"])

    async def reserve_aspect(self, params, state, box, connections):
        inventory = box.resolve(InventoryServiceResource).service
        reservation_id = await inventory.reserve(params.item_id, 1)
        return {"reservation_id": reservation_id}

    # Tests
    mock_payment = AsyncMock(spec=PaymentService)
    bench = TestBench(mocks={PaymentServiceResource: PaymentServiceResource(mock_payment)})

═══════════════════════════════════════════════════════════════════════════════
LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

This module defines only interfaces and intentionally raises
`NotImplementedError`. Behavior lives in mocks/fixtures.

Concrete ``@depends`` targets are ``*Resource`` subclasses of
:class:`~aoa.action_machine.resources.external_service.external_service_resource.ExternalServiceResource`
wrapping each client type (formal model: external services are resources).
"""


from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.resources.external_service.external_service_resource import (
    ExternalServiceResource,
)

from .domains import TestDomain


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


@meta(description="Payment service resource (test domain)", domain=TestDomain)
class PaymentServiceResource(ExternalServiceResource[PaymentService]):
    """Resource manager wrapping :class:`PaymentService` for ``@depends`` / mocks."""


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


@meta(description="Notification service resource (test domain)", domain=TestDomain)
class NotificationServiceResource(ExternalServiceResource[NotificationService]):
    """Resource manager wrapping :class:`NotificationService` for ``@depends`` / mocks."""


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


@meta(description="Inventory service resource (test domain)", domain=TestDomain)
class InventoryServiceResource(ExternalServiceResource[InventoryService]):
    """Resource manager wrapping :class:`InventoryService` for ``@depends`` / mocks."""


class SagaCompensateTraceService:
    """
    Test helper: compensators call this so tests assert rollback order and args.

    Not used in production actions; only in saga contract tests.
    """

    async def record_second_rollback(self, *, state_after_none: bool) -> None:
        """Record that the second aspect's compensator ran."""
        raise NotImplementedError(
            "SagaCompensateTraceService.record_second_rollback() is not implemented",
        )


@meta(description="Saga compensate trace resource (test domain)", domain=TestDomain)
class SagaCompensateTraceServiceResource(ExternalServiceResource[SagaCompensateTraceService]):
    """Resource manager wrapping :class:`SagaCompensateTraceService` for ``@depends`` / mocks."""


def default_payment_service_resource() -> PaymentServiceResource:
    return PaymentServiceResource(PaymentService())


def default_notification_service_resource() -> NotificationServiceResource:
    return NotificationServiceResource(NotificationService())


def default_inventory_service_resource() -> InventoryServiceResource:
    return InventoryServiceResource(InventoryService())


def default_saga_compensate_trace_service_resource() -> SagaCompensateTraceServiceResource:
    return SagaCompensateTraceServiceResource(SagaCompensateTraceService())
