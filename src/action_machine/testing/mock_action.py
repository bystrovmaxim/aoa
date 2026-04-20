# src/action_machine/testing/mock_action.py
"""
MockAction - mock action for test-time substitution.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

MockAction replaces real actions in tests by returning either a fixed result
or a value computed via ``side_effect``. It is used by TestBench for
dependency substitution.

MockAction is a full action with concrete schema types ``MockActionParams`` /
``MockActionResult`` so interchange graphs can resolve ``params`` / ``result``
edges without emitting rows for the abstract ``BaseParams`` / ``BaseResult`` axes.
It includes a summary aspect (``_mock_result_summary``), so it can run through
the full machine pipeline. However, TestBench calls ``run()`` directly for
MockAction to bypass aspect orchestration; this is faster and does not require
``@meta`` or ``@check_roles``.

═══════════════════════════════════════════════════════════════════════════════
MODES
═══════════════════════════════════════════════════════════════════════════════

1. Fixed result (``result``):
   ``MockAction(result=MyResult(...))`` always returns the same result object.

2. Computed result (``side_effect``):
   ``MockAction(side_effect=lambda p: MyResult(...))`` calls ``side_effect``
   on each run and returns its value.

3. If ``side_effect`` is set, ``result`` is ignored.

4. If neither ``result`` nor ``side_effect`` is set, ``run()`` raises
   ``ValueError``.

═══════════════════════════════════════════════════════════════════════════════
CALL COUNTER AND PARAMS
═══════════════════════════════════════════════════════════════════════════════

MockAction tracks invocation count (``call_count``) and stores params from the
last call (``last_params``). This lets tests assert call frequency and
arguments.

═══════════════════════════════════════════════════════════════════════════════
NAMING INVARIANT
═══════════════════════════════════════════════════════════════════════════════

MockAction ends with ``Action`` (BaseAction naming invariant). Its summary
method ends with ``_summary`` (``@summary_aspect`` naming invariant). The
summary description is mandatory.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.testing import MockAction, TestBench

    # Fixed result:
    mock = MockAction(result=OrderResult(order_id="ORD-1", status="ok"))
    result = mock.run(OrderParams(user_id="u1"))
    assert result.order_id == "ORD-1"
    assert mock.call_count == 1

    # Computed result:
    mock = MockAction(side_effect=lambda p: OrderResult(order_id=f"ORD-{p.user_id}"))
    result = mock.run(OrderParams(user_id="u42"))
    assert result.order_id == "ORD-u42"

    # In TestBench:
    bench = TestBench(mocks={
        PaymentService: MockAction(result=PayResult(txn_id="TXN-1")),
    })
"""

from collections.abc import Callable

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.tools_box import ToolsBox


class MockActionParams(BaseParams):
    """Concrete params type for :class:`MockAction` (interchange / schema binding)."""


class MockActionResult(BaseResult):
    """Concrete result type for :class:`MockAction` (interchange / schema binding)."""


class MockAction(BaseAction[MockActionParams, MockActionResult]):  # pylint: disable=too-many-ancestors
    """
    Mock action for tests.

    Replaces real action behavior with fixed or computed output and tracks call
    metadata for assertions.
    """

    def __init__(
        self,
        result: BaseResult | None = None,
        side_effect: Callable[[BaseParams], BaseResult] | None = None,
    ) -> None:
        """
        Initialize mock action.
        """
        self.result = result
        self.side_effect = side_effect
        self.call_count: int = 0
        self.last_params: BaseParams | None = None

    def run(self, params: BaseParams) -> BaseResult:
        """
        Execute mock action.

        Increments ``call_count``, stores ``last_params``, then returns
        ``side_effect(params)`` or ``result``.
        """
        self.call_count += 1
        self.last_params = params

        if self.side_effect:
            return self.side_effect(params)

        if self.result is None:
            raise ValueError("MockAction: neither result nor side_effect provided")

        return self.result

    @summary_aspect("MockAction summary aspect stub")
    async def _mock_result_summary(
        self,
        params: BaseParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> BaseResult:
        """
        Summary aspect stub for full-pipeline compatibility.

        Delegates to ``run(params)``.
        """
        return self.run(params)
