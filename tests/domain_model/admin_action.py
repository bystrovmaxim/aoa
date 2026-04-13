# tests/domain_model/admin_action.py
"""
AdminAction — role-restricted Action (``@check_roles(AdminRole)``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Only users assigned ``AdminRole`` may run it. One regular aspect with checker
and summary. No dependencies or connections. SystemDomain.

execute_admin builds a string with prefix "admin_processed:" into state
as admin_note. Summary returns Result with success=True and target from params.

═══════════════════════════════════════════════════════════════════════════════
USAGE IN TESTS
═══════════════════════════════════════════════════════════════════════════════

- Role tests: AdminRole passes; UserRole only or no roles → AuthorizationError.
- ``@check_roles(AdminRole)`` — один конкретный тип роли.
- run_aspect: execute_admin in isolation.

    admin_bench = bench.with_user(user_id="admin_1", roles=(AdminRole,))
    result = await admin_bench.run(
        AdminAction(),
        AdminAction.Params(target="user_456"),
        rollup=False,
    )
    assert result.success is True
    assert result.target == "user_456"

    user_bench = bench.with_user(user_id="user_1", roles=(UserRole,))
    with pytest.raises(AuthorizationError):
        await user_bench.run(
            AdminAction(),
            AdminAction.Params(target="user_456"),
            rollup=False,
        )
"""

from pydantic import Field

from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth import check_roles
from action_machine.intents.checkers import result_string
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.base_state import BaseState
from action_machine.resources.base_resource_manager import BaseResourceManager
from action_machine.runtime.tools_box import ToolsBox

from .domains import SystemDomain
from .roles import AdminRole


@meta(description="Administrative Action with restricted access", domain=SystemDomain)
@check_roles(AdminRole)
class AdminAction(BaseAction["AdminAction.Params", "AdminAction.Result"]):
    """
    Admin-only Action.

    Pipeline:
    1. execute_admin (regular) — admin_note with prefix.
       Checker: result_string("admin_note", required=True).
    2. build_result (summary) — Result with success and target.
    """

    class Params(BaseParams):
        """Admin Action parameters — operation target."""
        target: str = Field(
            description="Target of the administrative operation",
            examples=["user_456"],
        )

    class Result(BaseResult):
        """Admin Action result."""
        success: bool = Field(description="Whether the operation succeeded")
        target: str = Field(description="Processed target")

    @regular_aspect("Execute admin operation")
    @result_string("admin_note", required=True)
    async def execute_admin_aspect(
        self,
        params: "AdminAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict:
        """
        Run an administrative operation on the target.

        Builds admin_note as "admin_processed:{target}".

        Returns:
            dict with key admin_note.
        """
        return {"admin_note": f"admin_processed:{params.target}"}

    @summary_aspect("Build result")
    async def build_result_summary(
        self,
        params: "AdminAction.Params",
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> "AdminAction.Result":
        """
        Build administrative Result.

        Returns:
            AdminAction.Result with success=True and target from params.
        """
        return AdminAction.Result(
            success=True,
            target=params.target,
        )
