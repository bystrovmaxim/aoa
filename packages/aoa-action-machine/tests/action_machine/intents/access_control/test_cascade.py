"""The decision matrix: which caller, which step, which path — and what comes back.

Written against the machine's current paths (T011) and switched to the cascade once
it drives them (T015, T017). Today's ``level`` encodes the same distinction the five
gate words will publish, so every row carries both: the level it must answer today,
and the word it will answer with.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AuthorizationError
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles, grant
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

from ....support.domain_model.domains import SystemDomain
from ....support.domain_model.roles import AdminRole, ManagerRole, UserRole

_CALLS: dict[str, int] = {"when": 0, "guard": 0, "access_decide": 0, "summary": 0}


@pytest.fixture(autouse=True)
def _reset_calls() -> None:
    """Count every step call from zero for each test."""
    for key in _CALLS:
        _CALLS[key] = 0


def _when_never(user: Any) -> bool:
    """A declared condition that always refuses — and records that it was asked."""
    _CALLS["when"] += 1
    return False


def _guard_never(user: Any, params: Any) -> bool:
    """A shared condition that always refuses — and records that it was asked."""
    _CALLS["guard"] += 1
    return False


def _anonymous() -> Context:
    """A caller with no user at all."""
    return Context()


def _user_without_the_role() -> Context:
    """A caller who holds a role, just not the one the operation lists."""
    return Context(user=UserInfo(user_id="u-2", roles=(UserRole,)))


def _admin() -> Context:
    """A caller holding the role the operations below list."""
    return Context(user=UserInfo(user_id="u-1", roles=(AdminRole,)))


def _manager() -> Context:
    """A caller holding the role whose declared condition refuses."""
    return Context(user=UserInfo(user_id="u-3", roles=(ManagerRole,)))


@meta(description="matrix: role held, object allowed", domain=SystemDomain)
@check_roles(AdminRole)
class PlainAction(BaseAction["PlainAction.Params", "PlainAction.Result"]):
    """An operation whose declared caller may run it."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    async def access_decide(
        self, params: PlainAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> bool:
        """Allow the object, recording that the step was reached."""
        _CALLS["access_decide"] += 1
        return True

    @summary_aspect("S")
    async def probe_summary(
        self, params: PlainAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> PlainAction.Result:
        """Record that the operation itself was reached."""
        _CALLS["summary"] += 1
        return PlainAction.Result()


@meta(description="matrix: role missing", domain=SystemDomain)
@check_roles(AdminRole)
class RoleOnlyAction(BaseAction["RoleOnlyAction.Params", "RoleOnlyAction.Result"]):
    """An operation that lists a role the caller does not hold."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    async def access_decide(
        self, params: RoleOnlyAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> bool:
        """Allow the object if this step is ever reached."""
        _CALLS["access_decide"] += 1
        return True

    @summary_aspect("S")
    async def probe_summary(
        self, params: RoleOnlyAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> RoleOnlyAction.Result:
        """Record that the operation itself was reached."""
        _CALLS["summary"] += 1
        return RoleOnlyAction.Result()


@meta(description="matrix: a role matched, its condition refused", domain=SystemDomain)
@check_roles(grant(ManagerRole, when=_when_never))
class WhenAction(BaseAction["WhenAction.Params", "WhenAction.Result"]):
    """An operation whose grant carries a condition that refuses."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    async def access_decide(
        self, params: WhenAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> bool:
        """Allow the object if this step is ever reached."""
        _CALLS["access_decide"] += 1
        return True

    @summary_aspect("S")
    async def probe_summary(
        self, params: WhenAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> WhenAction.Result:
        """Record that the operation itself was reached."""
        _CALLS["summary"] += 1
        return WhenAction.Result()


@meta(description="matrix: the shared condition refused", domain=SystemDomain)
@check_roles(AdminRole, guard=_guard_never)
class GuardAction(BaseAction["GuardAction.Params", "GuardAction.Result"]):
    """An operation whose shared condition refuses."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    async def access_decide(
        self, params: GuardAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> bool:
        """Allow the object if this step is ever reached."""
        _CALLS["access_decide"] += 1
        return True

    @summary_aspect("S")
    async def probe_summary(
        self, params: GuardAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> GuardAction.Result:
        """Record that the operation itself was reached."""
        _CALLS["summary"] += 1
        return GuardAction.Result()


@meta(description="matrix: the object step refused", domain=SystemDomain)
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
        """Refuse the object, recording that the step was reached."""
        _CALLS["access_decide"] += 1
        return False

    @summary_aspect("S")
    async def probe_summary(
        self, params: ObjectDeniedAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> ObjectDeniedAction.Result:
        """Record that the operation itself was reached."""
        _CALLS["summary"] += 1
        return ObjectDeniedAction.Result()


@meta(description="matrix: the object step cannot tell", domain=SystemDomain)
@check_roles(AdminRole)
class ObjectCrashAction(BaseAction["ObjectCrashAction.Params", "ObjectCrashAction.Result"]):
    """An operation whose object check cannot tell."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    async def access_decide(
        self, params: ObjectCrashAction.Params, context: Context, box: ToolsBox, connections: dict[str, Any]
    ) -> bool:
        """Fail the way a store fails."""
        _CALLS["access_decide"] += 1
        raise RuntimeError("store is down")

    @summary_aspect("S")
    async def probe_summary(
        self, params: ObjectCrashAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> ObjectCrashAction.Result:
        """Record that the operation itself was reached."""
        _CALLS["summary"] += 1
        return ObjectCrashAction.Result()


@dataclass(frozen=True)
class Row:
    """One cell of the matrix: an operation, a caller, and what each path answers."""

    name: str
    action: Callable[[], BaseAction[Any, Any]]
    caller: Callable[[], Context]
    today_level: int | None
    word: str


ROWS = (
    Row("role held, object allowed", PlainAction, _admin, None, "allowed"),
    Row("no listed role is held", RoleOnlyAction, _user_without_the_role, 1, "CHECK_ROLES"),
    Row("role held, its condition refused", WhenAction, _manager, 2, "WHEN"),
    Row("the shared condition refused", GuardAction, _admin, 2, "GUARD"),
    Row("the object step refused", ObjectDeniedAction, _admin, 3, "ACCESS_DECIDE"),
)
"""The steps the machine can express today; the identity step lands with T018."""


@pytest.fixture(scope="module")
def machine() -> ActionProductMachine:
    """The machine under test, without a cache."""
    return ActionProductMachine(cache_coordinator=None)


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row.name)
async def test_the_execution_path_answers_each_step(machine: ActionProductMachine, row: Row) -> None:
    """An allowed call runs; a refused one fails with the level of the step that refused."""
    if row.today_level is None:
        await machine.run(row.caller(), row.action(), row.action().Params())
        return
    with pytest.raises(AuthorizationError) as excinfo:
        await machine.run(row.caller(), row.action(), row.action().Params())
    assert excinfo.value.level == row.today_level


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row.name)
async def test_the_question_path_answers_each_step(machine: ActionProductMachine, row: Row) -> None:
    """Asking in advance answers the same way, without running anything."""
    action = row.action()
    verdict = await machine.check_access_decide(row.caller(), type(action), action.Params())
    assert verdict.allowed is (row.today_level is None)
    assert verdict.level == row.today_level
    assert _CALLS["summary"] == 0


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row.name)
async def test_both_paths_agree(machine: ActionProductMachine, row: Row) -> None:
    """The advance answer and the executed outcome do not diverge for the same call."""
    action = row.action()
    verdict = await machine.check_access_decide(row.caller(), type(action), action.Params())
    try:
        await machine.run(row.caller(), row.action(), row.action().Params())
        executed_level = None
    except AuthorizationError as exc:
        executed_level = exc.level
    assert executed_level == verdict.level


def test_the_matrix_names_the_word_every_row_will_publish() -> None:
    """Each row already knows the word the cascade will answer with."""
    assert {row.word for row in ROWS} == {"allowed", "CHECK_ROLES", "WHEN", "GUARD", "ACCESS_DECIDE"}


async def test_a_step_that_refuses_stops_the_steps_after_it(machine: ActionProductMachine) -> None:
    """A refusal by an early step means the later steps are never asked."""
    with pytest.raises(AuthorizationError):
        await machine.run(_user_without_the_role(), RoleOnlyAction(), RoleOnlyAction.Params())
    assert _CALLS["access_decide"] == 0
    assert _CALLS["summary"] == 0

    with pytest.raises(AuthorizationError):
        await machine.run(_manager(), WhenAction(), WhenAction.Params())
    assert _CALLS["access_decide"] == 0

    with pytest.raises(AuthorizationError):
        await machine.run(_admin(), GuardAction(), GuardAction.Params())
    assert _CALLS["access_decide"] == 0


async def test_an_allowed_call_reaches_every_step(machine: ActionProductMachine) -> None:
    """When nothing refuses, the object step runs and the operation itself does too."""
    await machine.run(_admin(), PlainAction(), PlainAction.Params())
    assert _CALLS["access_decide"] == 1
    assert _CALLS["summary"] == 1


async def test_a_step_that_cannot_tell_is_answered_as_a_refusal_today(machine: ActionProductMachine) -> None:
    """The defect the cascade replaces: "I cannot tell" is reported as "not allowed".

    Today the question path answers ``allowed: False`` and puts the failure's own text
    into the reason, while the execution path lets the raw error escape. The cascade
    answers ``Undecided`` naming the step instead, and T017 flips this test.
    """
    action = ObjectCrashAction()
    verdict = await machine.check_access_decide(_admin(), ObjectCrashAction, action.Params())
    assert verdict.allowed is False
    assert verdict.level is None
    assert verdict.reason == "store is down"

    with pytest.raises(RuntimeError, match="store is down"):
        await machine.run(_admin(), ObjectCrashAction(), action.Params())
