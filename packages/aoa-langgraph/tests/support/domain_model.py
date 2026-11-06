"""
Self-contained test-support domain model for the aoa-langgraph package.

Faithful, trimmed copy of the action-machine scenario domain model, reduced to
only what the langgraph adapter tests touch: ``PingAction``, ``FullAction`` and
``OrdersStorage`` plus their definition-time closure (domains, the manager
role, and the two service resources used by ``FullAction``'s ``@depends`` /
``@connection``).

Symbol names are preserved exactly so the langgraph tests only need to change
their import lines. Imports come solely from ``aoa.action_machine.*`` and
third-party libraries — never from ``tests.*``.

Definition order is dependency-driven (domains → role → services → DB manager →
actions) because ``FullAction``'s decorators reference every dependency at
class-definition time.
"""

from pydantic import Field

from aoa.action_machine.auth.application_role import ApplicationRole
from aoa.action_machine.domain.base_domain import BaseDomain
from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import GuestRole, check_roles
from aoa.action_machine.intents.checkers import result_float, result_string
from aoa.action_machine.intents.connection import connection
from aoa.action_machine.intents.depends import depends
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources import BaseGateway, BaseStorage, Connections
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

# ─── Domains ──────────────────────────────────────────────────────────────────


class OrdersDomain(BaseDomain):
    """Orders domain — used for actions related to order processing."""

    name = "orders"
    description = "Domain for processing customer orders"


class SystemDomain(BaseDomain):
    """System domain — used for infrastructure actions (ping, health check)."""

    name = "system"
    description = "System domain for infrastructure operations"


class TestDomain(BaseDomain):
    """Generic domain for tests where the scenario does not care which domain is used."""

    name = "test"
    description = "Shared test domain for @meta"


# ─── Roles ────────────────────────────────────────────────────────────────────


@role_mode(RoleMode.ALIVE)
class ManagerRole(ApplicationRole):
    name = "manager"
    description = "Manager."


# ─── Services ─────────────────────────────────────────────────────────────────


class PaymentClient:
    """
    Payment processing service.

    Provides charge() for debits and refund() for refunds. In production
    this would talk to a payment gateway. In tests, use AsyncMock(spec=PaymentClient).
    """

    async def charge(self, amount: float, currency: str) -> str:
        """Charge funds and return a transaction id."""
        raise NotImplementedError("PaymentClient.charge() is not implemented")

    async def refund(self, txn_id: str) -> bool:
        """Refund a transaction by id."""
        raise NotImplementedError("PaymentClient.refund() is not implemented")


@meta(description="Payment gateway (test domain)", domain=TestDomain)
class PaymentGateway(BaseGateway):
    """The gateway to the payment service: its methods are what the domain asks of it."""

    def __init__(self, client: PaymentClient) -> None:
        self._client = client

    async def charge(self, amount: float, currency: str) -> str:
        """Charge funds and return a transaction id."""
        return await self._client.charge(amount, currency)

    async def refund(self, txn_id: str) -> bool:
        """Refund a transaction by id."""
        return await self._client.refund(txn_id)


class NotificationClient:
    """
    Notification service.

    Provides send() for user messages. In production: email/SMS/push.
    In tests: AsyncMock.
    """

    async def send(self, user_id: str, message: str) -> bool:
        """Send a notification to a user."""
        raise NotImplementedError("NotificationClient.send() is not implemented")


@meta(description="Notification gateway (test domain)", domain=TestDomain)
class NotificationGateway(BaseGateway):
    """The gateway to the notification service: its methods are what the domain asks of it."""

    def __init__(self, client: NotificationClient) -> None:
        self._client = client

    async def send(self, user_id: str, message: str) -> bool:
        """Send a notification to a user."""
        return await self._client.send(user_id, message)


def default_payment_gateway() -> PaymentGateway:
    return PaymentGateway(PaymentClient())


def default_notification_gateway() -> NotificationGateway:
    return NotificationGateway(NotificationClient())


# ─── DB manager (resource referenced by @depends / @connection) ───────────────


@meta(
    description="Test database resource manager for order-scenario actions",
    domain=OrdersDomain,
)
class OrdersStorage(BaseStorage):
    """Minimal manager; runtime tests use ``AsyncMock(spec=OrdersStorage)``."""

    @classmethod
    def get_wrapper_class(cls) -> type[BaseResource] | None:
        return None


# ─── Actions ──────────────────────────────────────────────────────────────────


@meta(description="Service health check", domain=SystemDomain)
@check_roles(GuestRole)
class PingAction(BaseAction["PingAction.Params", "PingAction.Result"]):
    """
    Minimal Action without parameters or dependencies.

    Summary-only aspect returning a fixed "pong" result. GuestRole.
    """

    class Params(BaseParams):
        """PingAction parameters — empty; no input required."""

        pass

    class Result(BaseResult):
        """PingAction result — pong message."""

        message: str = Field(description="Service response message")

    @summary_aspect("Build pong response")
    async def pong_summary(
        self,
        params: "PingAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> "PingAction.Result":
        """Return a fixed Result with message 'pong'."""
        return PingAction.Result(message="pong")


@meta(description="Create order with payment and notification", domain=OrdersDomain)
@check_roles(ManagerRole)
@depends(
    PaymentGateway,
    factory=default_payment_gateway,
    description="Payment processing service",
)
@depends(
    NotificationGateway,
    factory=default_notification_gateway,
    description="Notification service",
)
@depends(OrdersStorage, description="DB resource (class — same graph node as @connection)")
@connection(OrdersStorage, key="db", description="Primary database")
class FullAction(BaseAction["FullAction.Params", "FullAction.Result"]):
    """
    Full-featured Action: two regular + summary, depends, connection.

    Requires role "manager". ``@depends`` lists classes (services + ``OrdersStorage``);
    ``@connection(OrdersStorage, key="db")`` shares the same resource_manager node.
    """

    class Params(BaseParams):
        """Order creation parameters."""

        user_id: str = Field(
            description="User identifier",
            min_length=1,
            examples=["user_123"],
        )
        amount: float = Field(
            description="Order amount",
            gt=0,
            examples=[1500.0],
        )
        currency: str = Field(
            default="RUB",
            description="ISO 4217 currency code",
            pattern=r"^[A-Z]{3}$",
            examples=["RUB", "USD"],
        )

    class Result(BaseResult):
        """Order creation result."""

        order_id: str = Field(description="Created order identifier")
        txn_id: str = Field(description="Payment transaction identifier")
        total: float = Field(description="Order total amount")
        status: str = Field(description="Order status")

    @regular_aspect("Process payment")
    @result_string("txn_id", required=True, min_length=1)
    async def process_payment_aspect(
        self,
        params: "FullAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict:
        """Charge funds via PaymentClient and store the txn_id in state."""
        payment = await box.resolve(PaymentGateway)
        txn_id = await payment.charge(params.amount, params.currency)
        return {"txn_id": txn_id}

    @regular_aspect("Calculate total")
    @result_string("txn_id", required=True, min_length=1)
    @result_float("total", required=True, min_value=0.0)
    async def calc_total_aspect(
        self,
        params: "FullAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> dict:
        """Compute the order total (currently equal to params.amount)."""
        return {"txn_id": state["txn_id"], "total": params.amount}

    @summary_aspect("Build order result")
    async def build_result_summary(
        self,
        params: "FullAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: Connections,
    ) -> "FullAction.Result":
        """Notify the user and assemble the final Result from state."""
        notification = await box.resolve(NotificationGateway)
        await notification.send(params.user_id, f"Order created: {state['txn_id']}")

        return FullAction.Result(
            order_id=f"ORD-{params.user_id}",
            txn_id=state["txn_id"],
            total=state["total"],
            status="created",
        )
