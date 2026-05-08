# tests/scenarios/domain_model/simple_action.py
"""
SimpleAction — medium-complexity Action with one regular aspect.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

One regular aspect and one summary aspect. The regular aspect validates the
input name and writes validated_name to state. result_string ensures
validated_name is a non-empty string.

No dependencies or connections. NoneRole. Belongs to OrdersDomain.

═══════════════════════════════════════════════════════════════════════════════
USAGE IN TESTS
═══════════════════════════════════════════════════════════════════════════════

- Checker tests: result_string validates validated_name.
- run_aspect tests: validate_name in isolation.
- run_summary tests: state with validated_name → summary.
- Basic pipeline tests: regular → state → summary → result.

    result = await bench.run(
        SimpleAction(),
        SimpleAction.Params(name="Alice"),
        rollup=False,
    )
    assert result.greeting == "Hello, Alice!"
"""

from pydantic import Field

from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import NoneRole, check_roles
from aoa.action_machine.intents.checkers import result_string
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

from .domains import OrdersDomain


@meta(description="Simple Action with a single aspect", domain=OrdersDomain)
@check_roles(NoneRole)
class SimpleAction(BaseAction["SimpleAction.Params", "SimpleAction.Result"]):
    """
    Action with one regular aspect and one checker.

    Pipeline:
    1. validate_name (regular) — writes validated_name to state.
       Checker: result_string("validated_name", required=True, min_length=1).
    2. build_greeting (summary) — greeting from state.
    """

    class Params(BaseParams):
        """SimpleAction parameters — name to validate."""
        name: str = Field(
            description="Name to process",
            min_length=1,
            examples=["Alice"],
        )

    class Result(BaseResult):
        """SimpleAction result — greeting message."""
        greeting: str = Field(description="Greeting message")

    @regular_aspect("Validate name")
    @result_string("validated_name", required=True, min_length=1)
    async def validate_name_aspect(
        self,
        params: "SimpleAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> dict:
        """
        Validate and normalize the name from params.

        Writes validated_name — trimmed name. result_string checks
        non-empty string with length >= 1.

        Returns:
            dict with key validated_name.
        """
        return {"validated_name": params.name.strip()}

    @summary_aspect("Build greeting")
    async def build_greeting_summary(
        self,
        params: "SimpleAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> "SimpleAction.Result":
        """
        Build greeting from validated_name in state.

        Returns:
            SimpleAction.Result with greeting = "Hello, {name}!".
        """
        name = state["validated_name"]
        return SimpleAction.Result(greeting=f"Hello, {name}!")
