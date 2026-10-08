"""The cascade itself: the order, the first answer, and what a failure means.

These tests drive ``decide()`` with stand-in steps, so they pin the decision's own
rules — the fixed order, the first answer ending it, and a step that cannot tell
becoming an answer rather than a crash — without going through the machine (FR-002,
FR-003, FR-005, FR-007).
"""

from __future__ import annotations

import inspect
from typing import Any, cast

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.intents.access_control import (
    GATES,
    GATES_AT_OBJECT,
    GATES_BEFORE_RUN,
    Allowed,
    Gate,
    Refused,
    Undecided,
    Verdict,
    cascade,
    decide,
)
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.check_roles import check_roles, grant
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

from ....support.domain_model.domains import SystemDomain
from ....support.domain_model.roles import AdminRole, ManagerRole

_BOX = cast("ToolsBox", object())
"""The steps are handed a box; the stand-ins below never read it."""
_CONNECTIONS: dict[str, BaseResource] = {}


@meta(description="cascade: an operation whose object check refuses", domain=SystemDomain)
@check_roles(AdminRole)
class RefusingObjectAction(BaseAction["RefusingObjectAction.Params", "RefusingObjectAction.Result"]):
    """An operation that declares a check refusing with a reason of its own."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide
    async def refusing_object_access_decide(
        self,
        params: RefusingObjectAction.Params,
        context: Context,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Refused:
        """Refuse, naming the developer's own reason."""
        return Refused("the object is not yours")


@meta(description="cascade: an operation whose object check cannot tell", domain=SystemDomain)
@check_roles(AdminRole)
class ExplodingObjectAction(BaseAction["ExplodingObjectAction.Params", "ExplodingObjectAction.Result"]):
    """An operation whose declared check fails the way a store fails."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide
    async def exploding_object_access_decide(
        self,
        params: ExplodingObjectAction.Params,
        context: Context,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Fail to tell anything about the object."""
        raise RuntimeError("store is down")


@meta(description="cascade: a check that answers nothing at all", domain=SystemDomain)
@check_roles(AdminRole)
class MuteCheckAction(BaseAction["MuteCheckAction.Params", "MuteCheckAction.Result"]):
    """An operation whose declared check answers ``None`` — which is not an answer."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide
    async def mute_access_decide(
        self,
        params: MuteCheckAction.Params,
        context: Context,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Any:
        """Answer with nothing."""
        return None


@meta(description="cascade: a check that answers something else", domain=SystemDomain)
@check_roles(AdminRole)
class GarbledCheckAction(BaseAction["GarbledCheckAction.Params", "GarbledCheckAction.Result"]):
    """An operation whose declared check answers a ``bool`` — which is not an answer."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide
    async def garbled_access_decide(
        self,
        params: GarbledCheckAction.Params,
        context: Context,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Any:
        """Answer with a word the vocabulary does not know."""
        return True


@meta(description="cascade: a check that cannot tell by itself", domain=SystemDomain)
@check_roles(AdminRole)
class HesitantCheckAction(BaseAction["HesitantCheckAction.Params", "HesitantCheckAction.Result"]):
    """An operation whose declared check answers undecided on its own."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide
    async def hesitant_access_decide(
        self,
        params: HesitantCheckAction.Params,
        context: Context,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Undecided:
        """Answer that nobody can tell."""
        return Undecided(gate=Gate.ACCESS_DECIDE)


@meta(description="cascade: an operation that declares no object check", domain=SystemDomain)
@check_roles(AdminRole)
class SilentObjectAction(BaseAction["SilentObjectAction.Params", "SilentObjectAction.Result"]):
    """An operation with no object check at all."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""



def _never(_user: Any) -> bool:
    """A declared condition that always refuses."""
    return False


def _guard_never(_user: Any, _params: Any) -> bool:
    """A shared condition that always refuses."""
    return False


@meta(description="cascade: an operation that lists a role", domain=SystemDomain)
@check_roles(AdminRole)
class RoleGatedAction(BaseAction["RoleGatedAction.Params", "RoleGatedAction.Result"]):
    """An operation whose declared caller must hold a role."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


@meta(description="cascade: a matching role whose condition refuses", domain=SystemDomain)
@check_roles(grant(ManagerRole, when=_never, reason="CONDITION_NEVER"))
class ConditionRefusingAction(BaseAction["ConditionRefusingAction.Params", "ConditionRefusingAction.Result"]):
    """An operation whose only grant matches the role and then refuses by condition."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


@meta(description="cascade: an operation with a shared condition", domain=SystemDomain)
@check_roles(AdminRole, guard=_guard_never, guard_reason="GUARD_NEVER")
class GuardedAction(BaseAction["GuardedAction.Params", "GuardedAction.Result"]):
    """An operation whose shared condition refuses everyone."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


def _admin() -> Context:
    """A caller holding the role the probes list."""
    return Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))


def _manager() -> Context:
    """A caller holding the role whose declared condition refuses."""
    return Context(user=UserInfo(user_id="m1", roles=(ManagerRole,)))


def _stranger() -> Context:
    """A caller holding a role none of the probes list."""
    return Context(user=UserInfo(user_id="s1", roles=()))

def _install(monkeypatch: pytest.MonkeyPatch, calls: list[Gate], plan: dict[Gate, Any]) -> None:
    """Replace every step with a stand-in that records its gate and follows ``plan``."""
    for gate in GATES:

        async def step(
            context: Context,
            action: BaseAction[Any, Any],
            params: BaseParams | None,
            box: ToolsBox,
            connections: dict[str, BaseResource],
            _gate: Gate = gate,
        ) -> Verdict | None:
            calls.append(_gate)
            outcome = plan.get(_gate)
            if isinstance(outcome, Exception):
                raise outcome
            return cast("Verdict | None", outcome)

        monkeypatch.setitem(cascade._STEPS, gate, step)


def _install_object_step_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the real object step and let the three earlier ones pass."""
    for gate in GATES:
        if gate is Gate.ACCESS_DECIDE:
            continue
        monkeypatch.setitem(cascade._STEPS, gate, _passing_step)


async def _passing_step(
    context: Context,
    action: BaseAction[Any, Any],
    params: BaseParams | None,
    box: ToolsBox,
    connections: dict[str, BaseResource],
) -> Verdict | None:
    """A step that lets the decision continue."""
    return None


async def _run(action: BaseAction[Any, Any]) -> Any:
    """Decide for one call with parameters of the operation's own type."""
    return await decide(Context(), action, action.Params(), _BOX, _CONNECTIONS)


class TestTheOrderOfTheSteps:
    async def test_the_steps_run_in_the_declared_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[Gate] = []
        _install(monkeypatch, calls, {})

        result = await decide(Context(), SilentObjectAction(), SilentObjectAction.Params(), _BOX, _CONNECTIONS)

        assert calls == list(GATES)
        assert isinstance(result, Allowed)

    async def test_the_order_is_the_one_the_contract_publishes(self) -> None:
        assert GATES == (Gate.AUTH_COORDINATOR, Gate.CHECK_ROLES, Gate.GUARD, Gate.ACCESS_DECIDE)

    async def test_every_word_has_exactly_one_step(self) -> None:
        assert set(cascade._STEPS) == set(GATES)

    async def test_when_has_no_step_of_its_own(self) -> None:
        """``WHEN`` is answered by the roles step, so a failure there names ``CHECK_ROLES``."""
        assert Gate.WHEN not in cascade._STEPS


class TestTheFirstAnswerEndsTheDecision:
    async def test_a_refusal_ends_the_decision(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[Gate] = []
        refusal = Refused(gate=Gate.CHECK_ROLES)
        _install(monkeypatch, calls, {Gate.CHECK_ROLES: refusal})

        result = await decide(Context(), SilentObjectAction(), SilentObjectAction.Params(), _BOX, _CONNECTIONS)

        assert result == refusal
        assert calls == [Gate.AUTH_COORDINATOR, Gate.CHECK_ROLES]

    async def test_an_undecided_answer_ends_the_decision_too(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[Gate] = []
        undecided = Undecided(gate=Gate.GUARD)
        _install(monkeypatch, calls, {Gate.GUARD: undecided})

        result = await decide(Context(), SilentObjectAction(), SilentObjectAction.Params(), _BOX, _CONNECTIONS)

        assert result == undecided
        assert calls == [Gate.AUTH_COORDINATOR, Gate.CHECK_ROLES, Gate.GUARD]

    async def test_nothing_to_answer_is_allowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install(monkeypatch, [], {})

        result = await decide(Context(), SilentObjectAction(), SilentObjectAction.Params(), _BOX, _CONNECTIONS)

        assert isinstance(result, Allowed)


class TestAStepThatCannotTell:
    @pytest.mark.parametrize("failing_gate", GATES)
    async def test_a_failing_step_names_its_own_gate(
        self, monkeypatch: pytest.MonkeyPatch, failing_gate: Gate
    ) -> None:
        calls: list[Gate] = []
        _install(monkeypatch, calls, {failing_gate: RuntimeError("boom")})

        result = await decide(Context(), SilentObjectAction(), SilentObjectAction.Params(), _BOX, _CONNECTIONS)

        assert isinstance(result, Undecided)
        assert result.gate is failing_gate
        assert calls[-1] is failing_gate

    async def test_the_failure_is_carried_as_the_cause(self, monkeypatch: pytest.MonkeyPatch) -> None:
        failure = RuntimeError("boom")
        _install(monkeypatch, [], {Gate.GUARD: failure})

        result = await decide(Context(), SilentObjectAction(), SilentObjectAction.Params(), _BOX, _CONNECTIONS)

        assert isinstance(result, Undecided)
        assert result._cause is failure

    async def test_a_failure_is_not_a_refusal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install(monkeypatch, [], {Gate.CHECK_ROLES: RuntimeError("boom")})

        result = await decide(Context(), SilentObjectAction(), SilentObjectAction.Params(), _BOX, _CONNECTIONS)

        assert not isinstance(result, Refused)
        assert result.kind == "undecided"


class TestTheObjectStep:
    async def test_the_object_step_passes_when_the_operation_declares_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_object_step_only(monkeypatch)

        result = await _run(SilentObjectAction())

        assert isinstance(result, Allowed)

    async def test_the_object_step_carries_the_declared_answer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_object_step_only(monkeypatch)

        result = await _run(RefusingObjectAction())

        assert isinstance(result, Refused)
        assert result.reason == "the object is not yours"
        assert result.gate is Gate.ACCESS_DECIDE

    async def test_a_failing_object_check_is_undecided_naming_access_decide(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_object_step_only(monkeypatch)

        result = await _run(ExplodingObjectAction())

        assert isinstance(result, Undecided)
        assert result.gate is Gate.ACCESS_DECIDE
        assert isinstance(result._cause, RuntimeError)


class TestTheCascadePublishesNothing:
    def test_the_decision_has_nothing_to_publish_with(self) -> None:
        """No plugin context, no coordinator: deciding and publishing stay apart."""
        assert set(inspect.signature(decide).parameters) == {
            "context",
            "action",
            "params",
            "box",
            "connections",
            "gates",
        }


class TestTheTwoPhases:
    """The run exists between the phases, and only the machine knows when — so it asks twice."""

    async def test_the_two_phases_cover_every_step_in_order(self) -> None:
        assert GATES == GATES_BEFORE_RUN + GATES_AT_OBJECT

    async def test_the_object_step_is_not_in_the_phase_before_a_run(self) -> None:
        assert Gate.ACCESS_DECIDE not in GATES_BEFORE_RUN
        assert GATES_AT_OBJECT == (Gate.ACCESS_DECIDE,)

    async def test_the_phase_before_a_run_never_reaches_the_object_step(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[Gate] = []
        _install(monkeypatch, calls, {})

        result = await decide(
            Context(), SilentObjectAction(), SilentObjectAction.Params(), _BOX, _CONNECTIONS,
            gates=GATES_BEFORE_RUN,
        )

        assert isinstance(result, Allowed)
        assert calls == list(GATES_BEFORE_RUN)
        assert Gate.ACCESS_DECIDE not in calls

    async def test_the_object_phase_runs_that_step_alone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[Gate] = []
        _install(monkeypatch, calls, {})

        result = await decide(
            Context(), SilentObjectAction(), SilentObjectAction.Params(), _BOX, _CONNECTIONS,
            gates=GATES_AT_OBJECT,
        )

        assert isinstance(result, Allowed)
        assert calls == [Gate.ACCESS_DECIDE]

class TestTheRealSteps:
    """The steps the cascade actually runs, not stand-ins: each answers its own word."""

    async def test_a_caller_without_the_listed_role_is_refused_by_check_roles(self) -> None:
        result = await decide(_stranger(), RoleGatedAction(), RoleGatedAction.Params(), _BOX, _CONNECTIONS)

        assert isinstance(result, Refused)
        assert result.gate is Gate.CHECK_ROLES

    async def test_a_caller_holding_the_listed_role_is_allowed(self) -> None:
        result = await decide(_admin(), RoleGatedAction(), RoleGatedAction.Params(), _BOX, _CONNECTIONS)

        assert isinstance(result, Allowed)

    async def test_a_matching_role_whose_condition_refuses_is_refused_by_when(self) -> None:
        result = await decide(
            _manager(), ConditionRefusingAction(), ConditionRefusingAction.Params(), _BOX, _CONNECTIONS
        )

        assert isinstance(result, Refused)
        assert result.gate is Gate.WHEN

    async def test_a_shared_condition_that_refuses_is_refused_by_guard(self) -> None:
        result = await decide(_admin(), GuardedAction(), GuardedAction.Params(), _BOX, _CONNECTIONS)

        assert isinstance(result, Refused)
        assert result.gate is Gate.GUARD

    async def test_roles_are_answered_before_the_conditions(self) -> None:
        """A caller who fails both steps is told about the roles step, not the condition."""
        result = await decide(_stranger(), GuardedAction(), GuardedAction.Params(), _BOX, _CONNECTIONS)

        assert isinstance(result, Refused)
        assert result.gate is Gate.CHECK_ROLES

    async def test_every_probe_passes_when_nothing_refuses(self) -> None:
        @meta(description="cascade: an open operation", domain=SystemDomain)
        @check_roles(AdminRole, guard=lambda _user, _params: True, guard_reason="OPEN")
        class OpenAction(BaseAction["OpenAction.Params", "OpenAction.Result"]):
            """An operation whose condition allows everyone."""

            class Params(BaseParams):
                """No inputs."""

            class Result(BaseResult):
                """No outputs."""

        result = await decide(_admin(), OpenAction(), OpenAction.Params(), _BOX, _CONNECTIONS)

        assert isinstance(result, Allowed)

    async def test_an_answer_that_is_not_an_answer_is_not_read_as_allowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``None`` from a check used to pass the step; a mistake must never allow a call."""
        _install_object_step_only(monkeypatch)

        result = await _run(MuteCheckAction())

        assert isinstance(result, Undecided)
        assert not isinstance(result, Allowed)

    async def test_a_garbled_answer_is_undecided_naming_the_object_step(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install_object_step_only(monkeypatch)

        result = await _run(GarbledCheckAction())

        assert isinstance(result, Undecided)
        assert result.gate is Gate.ACCESS_DECIDE
        assert isinstance(result.cause, TypeError)

    async def test_the_mistake_is_named_in_the_cause(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _install_object_step_only(monkeypatch)

        result = await _run(GarbledCheckAction())

        assert isinstance(result, Undecided)
        assert isinstance(result.cause, TypeError)
        assert "answered True" in str(result.cause)

    async def test_a_check_that_cannot_tell_by_itself_is_carried_through(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An undecided the check decided is an answer, not a mistake."""
        _install_object_step_only(monkeypatch)

        result = await _run(HesitantCheckAction())

        assert isinstance(result, Undecided)
        assert result.gate is Gate.ACCESS_DECIDE
        assert result.cause is None
