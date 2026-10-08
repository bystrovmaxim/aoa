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
from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, Allowed, Undecided
from aoa.action_machine.intents.access_decide import access_decide
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

    @access_decide
    async def role_gated_access_decide(
        self, params: RoleGatedAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> Allowed:
        """Allow the object if this step is ever reached."""
        return Allowed()

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

    @access_decide
    async def guard_refused_access_decide(
        self, params: GuardRefusedAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> Allowed:
        """Allow the object if this step is ever reached."""
        return Allowed()

    @summary_aspect("S")
    async def probe_summary(
        self, params: GuardRefusedAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> GuardRefusedAction.Result:
        """Produce the operation's result."""
        return GuardRefusedAction.Result()


@meta(description="lifecycle: the object check answers something else", domain=SystemDomain)
@check_roles(AdminRole)
class ObjectGarbledAction(BaseAction["ObjectGarbledAction.Params", "ObjectGarbledAction.Result"]):
    """An operation whose check answers a word the vocabulary does not know."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide
    async def object_garbled_access_decide(
        self, params: ObjectGarbledAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> Any:
        """Answer with a ``bool``."""
        return True

    @summary_aspect("S")
    async def probe_summary(
        self, params: ObjectGarbledAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> ObjectGarbledAction.Result:
        """Produce the operation's result."""
        return ObjectGarbledAction.Result()


@meta(description="lifecycle: the object check could not tell", domain=SystemDomain)
@check_roles(AdminRole)
class ObjectCrashAction(BaseAction["ObjectCrashAction.Params", "ObjectCrashAction.Result"]):
    """An operation whose object check fails the way a store fails."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide
    async def object_crash_access_decide(
        self, params: ObjectCrashAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> Allowed:
        """Fail to tell anything about the object."""
        raise RuntimeError("store is down")

    @summary_aspect("S")
    async def probe_summary(
        self, params: ObjectCrashAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> ObjectCrashAction.Result:
        """Produce the operation's result."""
        return ObjectCrashAction.Result()


@meta(description="lifecycle: the object step refused", domain=SystemDomain)
@check_roles(AdminRole)
class ObjectDeniedAction(BaseAction["ObjectDeniedAction.Params", "ObjectDeniedAction.Result"]):
    """An operation whose object check refuses."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide
    async def object_denied_access_decide(
        self, params: ObjectDeniedAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> Allowed:
        """Refuse the object."""
        return FORBIDDEN_OBJECT

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

    @access_decide
    async def allowed_access_decide(
        self, params: AllowedAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> Allowed:
        """Allow the object."""
        return Allowed()

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
    """The object step runs after the run has started, so its refusal leaves a start — and
    the check announces itself, finishing with a refusal it decided."""
    with pytest.raises(AuthorizationError):
        await machine.run(_admin(), ObjectDeniedAction(), ObjectDeniedAction.Params())
    assert _SEEN == ["GlobalStartEvent", "BeforeAccessDecideAspectEvent", "AfterAccessDecideAspectEvent"]


async def test_an_allowed_call_runs_from_start_to_finish(machine: ActionProductMachine) -> None:
    """Nothing refuses: the run is announced, the operation runs, the run is closed."""
    await machine.run(_admin(), AllowedAction(), AllowedAction.Params())
    assert _SEEN[0] == "GlobalStartEvent"
    assert _SEEN[-1] == "GlobalFinishEvent"


@pytest.mark.parametrize(
    ("action", "caller", "expected"),
    [
        pytest.param(RoleGatedAction, _user_without_the_role, [], id="roles refused"),
        pytest.param(GuardRefusedAction, _admin, [], id="condition refused"),
        pytest.param(
            ObjectDeniedAction,
            _admin,
            ["BeforeAccessDecideAspectEvent", "AfterAccessDecideAspectEvent"],
            id="object refused",
        ),
        pytest.param(
            AllowedAction,
            _admin,
            ["BeforeAccessDecideAspectEvent", "AfterAccessDecideAspectEvent"],
            id="allowed",
        ),
    ],
)
async def test_the_question_path_announces_only_the_object_check(
    machine: ActionProductMachine,
    action: type[BaseAction[Any, Any]],
    caller: Any,
    expected: list[str],
) -> None:
    """Asking runs no step of the operation, so it has no run lifecycle — but the access
    checks are not steps of the operation: the object check runs, and announces itself."""
    await machine.check_access_decide(caller(), action, action.Params())
    assert expected == _SEEN


async def test_a_gate_that_cannot_tell_publishes_the_failed_gate(machine: ActionProductMachine) -> None:
    """A gate that breaks is the one thing about a decision an operator cannot see otherwise."""
    with pytest.raises(RuntimeError, match="store is down"):
        await machine.run(_admin(), ObjectCrashAction(), ObjectCrashAction.Params())

    assert "AccessGateFailedEvent" in _SEEN
    assert _SEEN[0] == "GlobalStartEvent"


async def test_asking_in_advance_publishes_no_failed_gate(machine: ActionProductMachine) -> None:
    """A question is answered, not announced: its failure is the answer's business."""
    verdict = await machine.check_access_decide(_admin(), ObjectCrashAction, ObjectCrashAction.Params())

    assert isinstance(verdict, Undecided)
    assert "AccessGateFailedEvent" not in _SEEN
    assert _SEEN == ["BeforeAccessDecideAspectEvent"]


async def test_a_garbled_answer_never_lets_a_call_through(machine: ActionProductMachine) -> None:
    """A check that answers something else is a developer's mistake, and it is loud."""
    with pytest.raises(TypeError, match="answered True"):
        await machine.run(_admin(), ObjectGarbledAction(), ObjectGarbledAction.Params())

    assert "GlobalStartEvent" in _SEEN
    assert "AfterAccessDecideAspectEvent" not in _SEEN


async def test_a_garbled_answer_is_undecided_when_asked_in_advance(machine: ActionProductMachine) -> None:
    verdict = await machine.check_access_decide(_admin(), ObjectGarbledAction, ObjectGarbledAction.Params())

    assert isinstance(verdict, Undecided)
    assert "answered True" not in str(verdict.model_dump())
