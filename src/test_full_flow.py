# src/test_full_flow.py
"""
Integration test demonstrating the full ActionMachine cycle:
- context creation,
- defining actions with aspects and logger,
- using dependencies (@depends),
- role checking (@CheckRoles),
- a plugin counting calls,
- logging via ConsoleLogger.

The test verifies that all components work together and the results are correct.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from action_machine.Auth.check_roles import CheckRoles
from action_machine.Checkers.StringFieldChecker import StringFieldChecker
from action_machine.Context.context import Context
from action_machine.Context.user_info import UserInfo
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Core.AspectMethod import aspect, depends, summary_aspect
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.BaseState import BaseState
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.Logging.console_logger import ConsoleLogger
from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.Plugins.Decorators import on
from action_machine.Plugins.Plugin import Plugin
from action_machine.Plugins.PluginEvent import PluginEvent
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager

# ----------------------------------------------------------------------
# Helper classes: parameters, results, dependencies
# ----------------------------------------------------------------------

@dataclass
class OrderParams(BaseParams):
    """Parameters for order creation."""
    user_id: str
    amount: float
    currency: str = "RUB"


@dataclass
class OrderResult(BaseResult):
    """Result of order creation."""
    order_id: str
    status: str
    total: float


class PaymentService:
    """Payment processing service (dependency)."""

    def __init__(self, gateway: str = "default"):
        self.gateway = gateway
        self.processed = []

    async def charge(self, amount: float, currency: str) -> str:
        """Charge funds (simulation)."""
        self.processed.append((amount, currency))
        return f"txn_{len(self.processed)}"


class NotificationService:
    """Notification service (dependency)."""

    def __init__(self):
        self.sent = []

    async def notify(self, user_id: str, message: str) -> None:
        """Send notification (simulation)."""
        self.sent.append((user_id, message))


# ----------------------------------------------------------------------
# Counter plugin
# ----------------------------------------------------------------------

class CounterPlugin(Plugin):
    """Plugin that counts calls of each action."""

    async def get_initial_state(self) -> dict[str, int]:
        """Initial state — empty counter."""
        return {}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def count_call(self, state: dict[str, int], event: PluginEvent) -> dict[str, int]:
        """Increment the counter for the given action."""
        action_name = event.action_name
        state[action_name] = state.get(action_name, 0) + 1
        return state


# ----------------------------------------------------------------------
# Actions
# ----------------------------------------------------------------------

@CheckRoles("user", desc="User can create orders")
@depends(PaymentService, description="Payment service")
@depends(NotificationService, description="Notification service")
class CreateOrderAction(BaseAction[OrderParams, OrderResult]):
    """Order creation action."""

    @aspect("Amount validation")
    async def validate_amount(
        self,
        params: OrderParams,
        state: BaseState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager],
        log: Any,  # ActionBoundLogger
    ) -> dict:
        """Check that the amount is positive."""
        await log.info("Validating amount - sum:{%var.amount} user: {%context.user.user_id}", amount=params.amount)
        if params.amount <= 0:
            raise ValueError("Amount must be positive")
        # Return empty dict because we don't add anything to state
        return {}

    @aspect("Payment processing")
    @StringFieldChecker("txn_id", "Transaction identifier", required=True)
    async def process_payment(
        self,
        params: OrderParams,
        state: BaseState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager],
        log: Any,
    ) -> dict:
        """Call PaymentService to charge funds."""
        payment = deps.get(PaymentService)
        txn_id = await payment.charge(params.amount, params.currency)
        await log.info("Payment processed", txn_id=txn_id)
        # Return dict with txn_id field, which has a checker
        return {"txn_id": txn_id}

    @summary_aspect("Build result")
    async def build_result(
        self,
        params: OrderParams,
        state: BaseState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager],
        log: Any,
    ) -> OrderResult:
        """Create result and send notification."""
        # Get data from state
        txn_id = state.get("txn_id")
        # Send notification
        notifier = deps.get(NotificationService)
        await notifier.notify(params.user_id, f"Order created, txn: {txn_id}")
        await log.info("Notification sent", user=params.user_id)
        return OrderResult(
            order_id=f"ORD_{params.user_id}_{id(params)}",
            status="created",
            total=params.amount,
        )


@CheckRoles(CheckRoles.NONE, desc="No authentication required")
class PingAction(BaseAction[BaseParams, BaseResult]):
    """Simple action without dependencies."""

    @summary_aspect("Reply pong")
    async def summary(
        self,
        params: BaseParams,
        state: BaseState,
        deps: DependencyFactory,
        connections: dict[str, BaseResourceManager],
        log: Any,
    ) -> BaseResult:
        await log.info("Ping received")
        result = BaseResult()
        result["message"] = "pong"
        return result


# ----------------------------------------------------------------------
# Integration test
# ----------------------------------------------------------------------

@pytest.mark.anyio
async def test_full_flow():
    """Full test running actions with machine, plugins, and logger."""

    # Create action instances to get class names
    create_order_action = CreateOrderAction()
    ping_action = PingAction()

    # 1. Create context with user
    user = UserInfo(user_id="bystrov.maxim", roles=["user"])
    context = Context(user=user)

    # 2. Set up logger (console, with colors)
    console_logger = ConsoleLogger(use_colors=True)
    log_coordinator = LogCoordinator(loggers=[console_logger])

    # 3. Create counter plugin
    counter_plugin = CounterPlugin()

    # 4. Create machine
    machine = ActionProductMachine(
        mode="integration-test-01",
        plugins=[counter_plugin],
        log_coordinator=log_coordinator,
    )

    # 5. Create dependency instances (external resources)
    payment_service = PaymentService(gateway="stripe")
    notification_service = NotificationService()

    # 6. Prepare parameters for the first action
    params1 = OrderParams(user_id="bystrov.maxim", amount=1500.0)

    # 7. Run action
    result1 = await machine.run(
        context=context,
        action=CreateOrderAction(),
        params=params1,
        resources={
            PaymentService: payment_service,
            NotificationService: notification_service,
        },
    )

    # 8. Assertions
    assert isinstance(result1, OrderResult)
    assert result1.status == "created"
    assert result1.total == 1500.0
    assert result1.order_id.startswith("ORD_bystrov.maxim_")

    # Check that dependencies were called
    assert len(payment_service.processed) == 1
    assert payment_service.processed[0] == (1500.0, "RUB")
    assert len(notification_service.sent) == 1
    assert notification_service.sent[0] == ("bystrov.maxim", "Order created, txn: txn_1")

    # 9. Run PingAction (no authentication)
    params2 = BaseParams()
    result2 = await machine.run(context, PingAction(), params2)

    assert result2["message"] == "pong"

    # 10. Check counter plugin state
    plugin_state = machine._plugin_coordinator._plugin_states[id(counter_plugin)]
    create_order_name = create_order_action.get_full_class_name()
    ping_name = ping_action.get_full_class_name()
    assert plugin_state.get(create_order_name) == 1
    assert plugin_state.get(ping_name) == 1

    # 11. Check that the logger was called (optional, could capture stdout)
    # In this test we just ensure the code runs without errors.
    # With the -s flag you'll see colored log output.


if __name__ == "__main__":
    asyncio.run(test_full_flow())
    print("✅ Integration test passed")