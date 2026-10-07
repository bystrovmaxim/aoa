"""Which lifecycle events a decision lets through, on each path.

The order of the steps decides this: the steps that run before anything starts
leave no trace when they refuse, the object step runs after the run has been
announced, and the question path runs nothing at all.
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AuthorizationError
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.intents.on.on_decorator import on
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.plugin.core.events import BasePluginEvent
from aoa.action_machine.plugin.core.plugin import Plugin
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

from ...support.domain_model.domains import SystemDomain
from ...support.domain_model.roles import AdminRole, ManagerRole, UserRole

_SEEN: list[str] = []


class LifecycleRecorder(Plugin):
    """A plugin that records the name of every event it is handed."""

    async def get_initial_state(self) -> dict[str, Any]:
        """Start with nothing recorded in the plugin's own state."""
        return {}

    @on(BasePluginEvent, ignore_exceptions=False)
    async def on_any(self, state: dict[str, Any], event: BasePluginEvent, log: Any) -> dict[str, Any]:
        """Record one event name."""
        _SEEN.append(type(event).__name__)
        return state


@pytest.fixture(autouse=True)
def _reset_seen() -> None:
    """Forget the events of the previous test."""
    _SEEN.clear()


@pytest.fixture
def machine() -> ActionProductMachine:
    """A machine that watches its own lifecycle through the recorder plugin."""
    return ActionProductMachine(cache_coordinator=None, plugins=[LifecycleRecorder()])


def _admin() -> Context:
    """A caller holding the role the operations below list."""
    return Context(user=UserInfo(user_id="u-1", roles=(AdminRole,)))


def _user_without_the_role() -> Context:
    """A caller who holds a role, just not the one the operation lists."""
    return Context(user=UserInfo(user_id="u-2", roles=(UserRole,)))


def _manager() -> Context:
    """A caller holding the role whose declared condition refuses."""
    return Context(user=UserInfo(user_id="u-3", roles=(ManagerRole,)))


def _guard_never(user: Any, params: Any) -> bool:
    """A shared condition that always refuses."""
    return False


@meta(description="lifecycle: role missing", domain=SystemDomain)
@check_roles(AdminRole)
class RoleGatedAction(BaseAction["RoleGatedAction.Params", "RoleGatedAction.Result"]):
    """An operation that lists a role the caller may not hold."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    async def access_decide(
        self, params: RoleGatedAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> bool:
        """Allow the object if this step is ever reached."""
        return True

    @summary_aspect("S")
    async def probe_summary(
        self, params: RoleGatedAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> RoleGatedAction.Result:
        """Produce the operation's result."""
        return RoleGatedAction.Result()


@meta(description="lifecycle: the shared condition refused", domain=SystemDomain)
@check_roles(AdminRole, guard=_guard_never)
class GuardRefusedAction(BaseAction["GuardRefusedAction.Params", "GuardRefusedAction.Result"]):
    """An operation whose shared condition refuses."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    async def access_decide(
        self, params: GuardRefusedAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> bool:
        """Allow the object if this step is ever reached."""
        return True

    @summary_aspect("S")
    async def probe_summary(
        self, params: GuardRefusedAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> GuardRefusedAction.Result:
        """Produce the operation's result."""
        return GuardRefusedAction.Result()


@meta(description="lifecycle: the object step refused", domain=SystemDomain)
@check_roles(AdminRole)
class ObjectDeniedAction(BaseAction["ObjectDeniedAction.Params", "ObjectDeniedAction.Result"]):
    """An operation whose object check refuses."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    async def access_decide(
        self, params: ObjectDeniedAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> bool:
        """Refuse the object."""
        return False

    @summary_aspect("S")
    async def probe_summary(
        self, params: ObjectDeniedAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> ObjectDeniedAction.Result:
        """Produce the operation's result."""
        return ObjectDeniedAction.Result()


@meta(description="lifecycle: everything allowed", domain=SystemDomain)
@check_roles(AdminRole)
class AllowedAction(BaseAction["AllowedAction.Params", "AllowedAction.Result"]):
    """An operation nothing refuses."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    async def access_decide(
        self, params: AllowedAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> bool:
        """Allow the object."""
        return True

    @summary_aspect("S")
    async def probe_summary(
        self, params: AllowedAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> AllowedAction.Result:
        """Produce the operation's result."""
        return AllowedAction.Result()


async def test_a_step_before_the_run_refuses_without_announcing_anything(machine: ActionProductMachine) -> None:
    """A refusal by the roles step leaves no lifecycle event at all: nothing had started."""
    with pytest.raises(AuthorizationError):
        await machine.run(_user_without_the_role(), RoleGatedAction(), RoleGatedAction.Params())
    assert _SEEN == []


async def test_a_condition_that_refuses_before_the_run_announces_nothing(machine: ActionProductMachine) -> None:
    """The same holds for the shared condition: it decides before the run is announced."""
    with pytest.raises(AuthorizationError):
        await machine.run(_admin(), GuardRefusedAction(), GuardRefusedAction.Params())
    assert _SEEN == []


async def test_the_object_step_refuses_after_the_run_was_announced(machine: ActionProductMachine) -> None:
    """The object step runs after the run has started, so its refusal still leaves a start."""
    with pytest.raises(AuthorizationError):
        await machine.run(_admin(), ObjectDeniedAction(), ObjectDeniedAction.Params())
    assert _SEEN == ["GlobalStartEvent"]


async def test_an_allowed_call_runs_from_start_to_finish(machine: ActionProductMachine) -> None:
    """Nothing refuses: the run is announced, the operation runs, the run is closed."""
    await machine.run(_admin(), AllowedAction(), AllowedAction.Params())
    assert _SEEN[0] == "GlobalStartEvent"
    assert _SEEN[-1] == "GlobalFinishEvent"


@pytest.mark.parametrize(
    ("action", "caller"),
    [
        pytest.param(RoleGatedAction, _user_without_the_role, id="roles refused"),
        pytest.param(GuardRefusedAction, _admin, id="condition refused"),
        pytest.param(ObjectDeniedAction, _admin, id="object refused"),
        pytest.param(AllowedAction, _admin, id="allowed"),
    ],
)
async def test_the_question_path_announces_nothing(
    machine: ActionProductMachine,
    action: type[BaseAction[Any, Any]],
    caller: Any,
) -> None:
    """Asking in advance runs no step of the operation, so it has no lifecycle to announce."""
    await machine.check_access_decide(caller(), action, action.Params())
    assert _SEEN == []
