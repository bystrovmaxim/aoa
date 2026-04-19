# tests/scenarios/domain_model/full_action.py
"""
FullAction — full-featured Action with dependencies and connections.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

The richest Action in the test domain: two regular aspects with checkers,
one summary aspect, two service dependencies (PaymentService, NotificationService),
``@depends(TestDbManager)`` and ``@connection(TestDbManager)`` — **class references**, same
as ``@depends(PaymentService)``; graph merges to one ``resource_manager`` node. Role "manager".

Exercises role checks, connection validation, dependency resolution via
box.resolve(), per-aspect checkers, and building the result from state.

═══════════════════════════════════════════════════════════════════════════════
ASPECT PIPELINE
═══════════════════════════════════════════════════════════════════════════════

    1. process_payment (regular)
       - Resolves PaymentService via box.resolve().
       - Calls payment.charge(amount, currency).
       - Writes txn_id to state.
       - Checker: result_string("txn_id", required=True, min_length=1).

    2. calc_total (regular)
       - Computes the order total.
       - Writes total to state.
       - Checker: result_float("total", required=True, min_value=0.0).

    3. build_result (summary)
       - Resolves NotificationService via box.resolve().
       - Sends a notification to the user.
       - Builds Result from state (txn_id, total).

═══════════════════════════════════════════════════════════════════════════════
USAGE IN TESTS
═══════════════════════════════════════════════════════════════════════════════

- Role tests: only "manager" passes; "user" gets AuthorizationError.
- Connection tests: "db" required; wrong/missing keys fail.
- Depends tests: PaymentService and NotificationService are mocked.
- Checker tests: txn_id (string), total (float).
- run_aspect tests: process_payment and calc_total individually.
- run_summary tests: state with txn_id and total → Result.
- Rollup tests: rollup passed through resolve and connections.

    mock_payment = AsyncMock(spec=PaymentService)
    mock_payment.charge.return_value = "TXN-001"
    mock_notification = AsyncMock(spec=NotificationService)
    mock_db = AsyncMock(spec=TestDbManager)

    bench = TestBench(
        mocks={PaymentService: mock_payment, NotificationService: mock_notification},
    ).with_user(user_id="mgr_1", roles=(ManagerRole,))

    result = await bench.run(
        FullAction(),
        FullAction.Params(user_id="user_123", amount=1500.0),
        rollup=False,
        connections={"db": mock_db},
    )
    assert result.order_id == "ORD-user_123"
    assert result.txn_id == "TXN-001"
"""

from pydantic import Field

from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import check_roles
from action_machine.intents.checkers import result_float, result_string
from action_machine.intents.connection import connection
from action_machine.intents.depends import depends
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.tools_box import ToolsBox

from .domains import OrdersDomain
from .roles import ManagerRole
from .services import NotificationService, PaymentService
from .test_db_manager import TestDbManager


@meta(description="Create order with payment and notification", domain=OrdersDomain)
@check_roles(ManagerRole)
@depends(PaymentService, description="Payment processing service")
@depends(NotificationService, description="Notification service")
@depends(TestDbManager, description="DB resource (class — same vertex as @connection)")
@connection(TestDbManager, key="db", description="Primary database")
class FullAction(BaseAction["FullAction.Params", "FullAction.Result"]):
    """
    Full-featured Action: two regular + summary, depends, connection.

    Requires role "manager". ``@depends`` lists classes (services + ``TestDbManager``);
    ``@connection(TestDbManager, key="db")`` shares the same resource_manager node.
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
        connections: dict[str, BaseResourceManager],
    ) -> dict:
        """
        Charge funds via PaymentService.

        Resolves PaymentService from box, calls charge() with amount and
        currency from params, stores returned txn_id in state.

        Returns:
            dict with key txn_id — transaction identifier.
        """
        payment = box.resolve(PaymentService)
        txn_id = await payment.charge(params.amount, params.currency)
        return {"txn_id": txn_id}

    @regular_aspect("Calculate total")
    @result_float("total", required=True, min_value=0.0)
    async def calc_total_aspect(
        self,
        params: "FullAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict:
        """
        Compute order total.

        Current implementation: total equals params.amount.
        A real system might apply discounts, tax, etc.

        Returns:
            dict with key total — final amount.
        """
        return {"total": params.amount}

    @summary_aspect("Build order result")
    async def build_result_summary(
        self,
        params: "FullAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> "FullAction.Result":
        """
        Build the final Result from state.

        Resolves NotificationService and notifies the user that the order
        was created. Assembles Result from txn_id and total produced by
        regular aspects.

        Returns:
            FullAction.Result with order_id, txn_id, total, status.
        """
        notification = box.resolve(NotificationService)
        await notification.send(params.user_id, f"Order created: {state['txn_id']}")

        return FullAction.Result(
            order_id=f"ORD-{params.user_id}",
            txn_id=state["txn_id"],
            total=state["total"],
            status="created",
        )
