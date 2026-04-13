# tests/scenarios/domain_model/child_action.py
"""
ChildAction — nested Action for box.run() tests.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Designed to be invoked from another Action via box.run(). One regular aspect
and summary. No dependencies or connections. NoneRole. SystemDomain.

process_aspect takes a string from params and returns it with prefix
"processed:". Summary builds Result from state.

═══════════════════════════════════════════════════════════════════════════════
USAGE IN TESTS
═══════════════════════════════════════════════════════════════════════════════

- Nesting: root Action calls ChildAction via
  box.run(ChildAction, ChildAction.Params(value="test")).
- nest_level increases on nested runs.
- WrapperSqlConnectionManager: connections passed into box.run() reach the child.
- Rollup: rollup propagates through box.run().

    async def some_aspect(self, params, state, box, connections):
        child_result = await box.run(
            ChildAction,
            ChildAction.Params(value="hello"),
        )
        assert child_result.processed == "processed:hello"

    result = await bench.run(
        ChildAction(),
        ChildAction.Params(value="world"),
        rollup=False,
    )
    assert result.processed == "processed:world"
"""

from pydantic import Field

from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth import NoneRole, check_roles
from action_machine.intents.checkers import result_string
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.tools_box import ToolsBox

from .domains import SystemDomain


@meta(description="Child Action for nested runs", domain=SystemDomain)
@check_roles(NoneRole)
class ChildAction(BaseAction["ChildAction.Params", "ChildAction.Result"]):
    """
    Action for nested invocation via box.run().

    Pipeline:
    1. process_aspect (regular) — prefix "processed:" to value.
       Checker: result_string("processed_value", required=True).
    2. build_result_summary (summary) — Result from state.
    """

    class Params(BaseParams):
        """Child Action parameters — string to process."""
        value: str = Field(
            description="Value to process",
            examples=["test_value"],
        )

    class Result(BaseResult):
        """Child Action result — processed value."""
        processed: str = Field(description="Processed value with prefix")

    @regular_aspect("Process value")
    @result_string("processed_value", required=True)
    async def process_aspect(
        self,
        params: "ChildAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict:
        """
        Prefix "processed:" to params.value.

        Returns:
            dict with key processed_value.
        """
        return {"processed_value": f"processed:{params.value}"}

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: "ChildAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> "ChildAction.Result":
        """
        Build Result from processed_value in state.

        Returns:
            ChildAction.Result with field processed.
        """
        return ChildAction.Result(processed=state["processed_value"])
