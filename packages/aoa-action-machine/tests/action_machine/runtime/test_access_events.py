# packages/aoa-action-machine/tests/action_machine/runtime/test_access_events.py
"""
Which events a decision publishes — the whole matrix, kept in memory (FR-013, FR-019,
FR-021, SC-001, SC-007, SC-008).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

An operator watching a service needs to see a decision being made and a gate failing,
and must never see what the caller was not told. This module pins that, cell by cell:
four points the decision can stop at, three situations at each, two modes of being asked.

The rules the matrix comes from:

- the run is announced only once the early gates have let the call through, so a refusal
  there leaves nothing behind, while a call stopped at the object step keeps its
  ``GlobalStart`` without a ``GlobalFinish``;
- asking in advance runs nothing, so it publishes no lifecycle and no failure;
- the object check announces itself when it is declared: a ``before`` whenever it starts,
  an ``after`` whenever it finishes;
- a gate that could not tell publishes one failed-gate event naming itself, and only while
  a call executes;
- the failure's kind travels, its text never does.

The cells where a gate could not tell are red until the machine raises ``AccessUndecided``
instead of re-raising the failure (T044). They are written this way on purpose: this task
states the contract, and the implementation tasks make it true.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestTheDecisionMatrix   — every cell of the contract's matrix, executing and asking
TestOneFailedGateEvent  — exactly one, naming the step, and only while executing
TestTheRequestIdentity  — carried when the context has one, absent when it has none
TestNoFailureText       — the failure's text reaches no attribute and no message

The recorder below is an exporter that keeps everything in memory instead of shipping it:
what a real exporter would receive is exactly what is asserted here.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.request_info import RequestInfo
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AccessDenied, AccessUndecided
from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, Allowed, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles, grant
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.intents.on.on_decorator import on
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.plugin.core.events import BasePluginEvent
from aoa.action_machine.plugin.core.plugin import Plugin
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

from ...support.domain_model.domains import SystemDomain
from ...support.domain_model.roles import AdminRole

_SECRET = "postgres://primary:5432 refused the connection"
"""A failure's text: nothing an answer and no event may carry."""

_DECISION_EVENTS = frozenset(
    {
        "GlobalStartEvent",
        "GlobalFinishEvent",
        "BeforeAccessDecideAspectEvent",
        "AfterAccessDecideAspectEvent",
        "AccessGateFailedEvent",
    }
)
"""The events a decision can publish; aspect and saga events belong to the pipeline."""

_HEAVY = frozenset({"context", "params", "action_class", "state_snapshot"})
"""Fields left out of a recorded payload: they hold objects, not attributes a reader reads."""

_RUN_START = "GlobalStartEvent"
_RUN_FINISH = "GlobalFinishEvent"
_BEFORE = "BeforeAccessDecideAspectEvent"
_AFTER = "AfterAccessDecideAspectEvent"
_FAILED = "AccessGateFailedEvent"

_BEHAVIOURS = ("allowed", "refused", "failed")
_OBJECT_BEHAVIOUR = "allowed"
"""Which object answer the probe gives; set for one test by the helpers below."""

_OBJECT_CELLS = {
    "object allowed": "allowed",
    "object refused": "refused",
    "object could not tell": "failed",
}
"""Which way the object check answers, per matrix cell."""


def _fail_when(user: Any) -> bool:
    """A role condition that cannot complete."""
    raise ConnectionError(_SECRET)


def _fail_guard(user: Any, params: Any) -> bool:
    """A shared condition that cannot complete."""
    raise ConnectionError(_SECRET)


def _allow_guard(user: Any, params: Any) -> bool:
    """A shared condition that lets everyone through."""
    return True


def _refuse_guard(user: Any, params: Any) -> bool:
    """A shared condition that refuses everyone."""
    return False


@meta(description="events: a bare role requirement", domain=SystemDomain)
@check_roles(AdminRole)
class RolesOnlyAction(BaseAction["RolesOnlyAction.Params", "RolesOnlyAction.Result"]):
    """An operation that lists a role and declares nothing else."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @summary_aspect("S")
    async def roles_summary(
        self, params: RolesOnlyAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> RolesOnlyAction.Result:
        """Produce the operation's result."""
        return RolesOnlyAction.Result()


@meta(description="events: a role condition that cannot complete", domain=SystemDomain)
@check_roles(grant(AdminRole, when=_fail_when, reason="CONDITION_FAILED"))
class ConditionFailsAction(BaseAction["ConditionFailsAction.Params", "ConditionFailsAction.Result"]):
    """An operation whose matching role's condition cannot be evaluated."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


@meta(description="events: a shared condition that allows", domain=SystemDomain)
@check_roles(AdminRole, guard=_allow_guard, guard_reason="GUARD_ALLOWS")
class GuardAllowsAction(BaseAction["GuardAllowsAction.Params", "GuardAllowsAction.Result"]):
    """An operation whose shared condition lets everyone through."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @summary_aspect("S")
    async def guard_summary(
        self, params: GuardAllowsAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> GuardAllowsAction.Result:
        """Produce the operation's result."""
        return GuardAllowsAction.Result()


@meta(description="events: a shared condition that refuses", domain=SystemDomain)
@check_roles(AdminRole, guard=_refuse_guard, guard_reason="SHOP_CLOSED")
class GuardRefusesAction(BaseAction["GuardRefusesAction.Params", "GuardRefusesAction.Result"]):
    """An operation whose shared condition refuses everyone."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


@meta(description="events: a shared condition that cannot complete", domain=SystemDomain)
@check_roles(AdminRole, guard=_fail_guard, guard_reason="GUARD_FAILED")
class GuardFailsAction(BaseAction["GuardFailsAction.Params", "GuardFailsAction.Result"]):
    """An operation whose shared condition cannot be evaluated."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


@meta(description="events: an object check that answers three ways", domain=SystemDomain)
@check_roles(AdminRole)
class ObjectCheckedAction(BaseAction["ObjectCheckedAction.Params", "ObjectCheckedAction.Result"]):
    """An operation whose object check allows, refuses or cannot tell, as the test asks."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide("Answer the way the test set up")
    async def object_checked_access_decide(
        self,
        params: ObjectCheckedAction.Params,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """Answer the way the test set up, failing with a text nobody may see."""
        if _OBJECT_BEHAVIOUR == "failed":
            raise ConnectionError(_SECRET)
        if _OBJECT_BEHAVIOUR == "refused":
            return FORBIDDEN_OBJECT
        return Allowed()

    @summary_aspect("S")
    async def object_summary(
        self, params: ObjectCheckedAction.Params, state: BaseState, box: ToolsBox, connections: dict[str, Any]
    ) -> ObjectCheckedAction.Result:
        """Produce the operation's result."""
        return ObjectCheckedAction.Result()


@dataclass(frozen=True)
class Record:
    """One event as an exporter would receive it."""

    name: str
    payload: dict[str, Any]
    trace_id: str | None
    text: str


class InMemoryExporter(Plugin):
    """A plugin that keeps every event it is handed, in memory."""

    def __init__(self) -> None:
        self.records: list[Record] = []

    async def get_initial_state(self) -> dict[str, Any]:
        """Start with nothing recorded."""
        return {}

    @on(BasePluginEvent, ignore_exceptions=False)
    async def on_any(self, state: dict[str, Any], event: BasePluginEvent, log: Any) -> dict[str, Any]:
        """Keep one event: its name, its attributes, the identity and its whole text."""
        payload: dict[str, Any] = {}
        if is_dataclass(event):
            payload = {
                field.name: getattr(event, field.name) for field in fields(event) if field.name not in _HEAVY
            }
        self.records.append(
            Record(
                name=type(event).__name__,
                payload=payload,
                trace_id=event.context.request.trace_id,
                text=str(event),
            )
        )
        return state

    def decision_events(self) -> list[str]:
        """The recorded events a decision can publish, in order."""
        return [record.name for record in self.records if record.name in _DECISION_EVENTS]


@pytest.fixture
def exporter() -> InMemoryExporter:
    """An exporter for one test."""
    return InMemoryExporter()


@pytest.fixture
def machine(exporter: InMemoryExporter) -> ActionProductMachine:
    """A machine watched by that exporter."""
    return ActionProductMachine(cache_coordinator=None, plugins=[exporter])


@pytest.fixture(autouse=True)
def _reset_behaviour() -> Any:
    """Let every test start from an object check that allows."""
    _set_object_behaviour("allowed")
    yield
    _set_object_behaviour("allowed")


def _set_object_behaviour(behaviour: str) -> None:
    """Aim the object check for one test."""
    global _OBJECT_BEHAVIOUR
    _OBJECT_BEHAVIOUR = behaviour


def _aim_object_check(situation: str) -> None:
    """Aim the object check when the cell is an object cell, and leave the others alone."""
    if situation in _OBJECT_CELLS:
        _set_object_behaviour(_OBJECT_CELLS[situation])


def _admin(trace_id: str | None = None) -> Context:
    """A caller holding the role every probe lists, optionally with a request identity."""
    return Context(user=UserInfo(user_id="u-1", roles=(AdminRole,)), request=RequestInfo(trace_id=trace_id))


def _stranger() -> Context:
    """A caller holding none of the listed roles."""
    return Context(user=UserInfo(user_id="u-2", roles=()))


def _early_probe(situation: str) -> tuple[type[BaseAction[Any, Any]], Context]:
    """Return the operation and caller that put an early gate in the named situation."""
    if situation == "roles allowed":
        return RolesOnlyAction, _admin()
    if situation == "roles refused":
        return RolesOnlyAction, _stranger()
    if situation == "roles could not tell":
        return ConditionFailsAction, _admin()
    if situation == "guard allowed":
        return GuardAllowsAction, _admin()
    if situation == "guard refused":
        return GuardRefusesAction, _admin()
    if situation == "guard could not tell":
        return GuardFailsAction, _admin()
    raise AssertionError(f"unknown situation: {situation}")


def _case(situation: str) -> tuple[type[BaseAction[Any, Any]], Context]:
    """Return the operation and caller for one cell, object cells included."""
    if situation in _OBJECT_CELLS:
        return ObjectCheckedAction, _admin()
    return _early_probe(situation)


async def _execute(
    machine: ActionProductMachine,
    action: type[BaseAction[Any, Any]],
    caller: Context,
    *,
    stops: bool,
) -> None:
    """Run a call: a stopping cell ends in one of the two answers, an allowed one does not."""
    if stops:
        with pytest.raises((AccessDenied, AccessUndecided)):
            await machine.run(caller, action(), action.Params())
        return
    await machine.run(caller, action(), action.Params())


_EXECUTE_CASES = [
    pytest.param("roles allowed", [_RUN_START, _RUN_FINISH], id="roles allowed"),
    pytest.param("roles refused", [], id="roles refused"),
    pytest.param("roles could not tell", [_FAILED], id="roles could not tell"),
    pytest.param("guard allowed", [_RUN_START, _RUN_FINISH], id="guard allowed"),
    pytest.param("guard refused", [], id="guard refused"),
    pytest.param("guard could not tell", [_FAILED], id="guard could not tell"),
    pytest.param("object allowed", [_RUN_START, _BEFORE, _AFTER, _RUN_FINISH], id="object allowed"),
    pytest.param("object refused", [_RUN_START, _BEFORE, _AFTER], id="object refused"),
    pytest.param("object could not tell", [_RUN_START, _BEFORE, _FAILED], id="object could not tell"),
]

_ASK_CASES = [
    pytest.param("roles allowed", [], id="roles allowed"),
    pytest.param("roles refused", [], id="roles refused"),
    pytest.param("roles could not tell", [], id="roles could not tell"),
    pytest.param("guard allowed", [], id="guard allowed"),
    pytest.param("guard refused", [], id="guard refused"),
    pytest.param("guard could not tell", [], id="guard could not tell"),
    pytest.param("object allowed", [_BEFORE, _AFTER], id="object allowed"),
    pytest.param("object refused", [_BEFORE, _AFTER], id="object refused"),
    pytest.param("object could not tell", [_BEFORE], id="object could not tell"),
]


class TestTheDecisionMatrix:
    @pytest.mark.parametrize(("situation", "expected"), _EXECUTE_CASES)
    async def test_executing_publishes_exactly_this(
        self, machine: ActionProductMachine, exporter: InMemoryExporter, situation: str, expected: list[str]
    ) -> None:
        _aim_object_check(situation)
        action, caller = _case(situation)

        await _execute(machine, action, caller, stops=_RUN_FINISH not in expected)

        assert exporter.decision_events() == expected

    @pytest.mark.parametrize(("situation", "expected"), _ASK_CASES)
    async def test_asking_in_advance_publishes_exactly_this(
        self, machine: ActionProductMachine, exporter: InMemoryExporter, situation: str, expected: list[str]
    ) -> None:
        _aim_object_check(situation)
        action, caller = _case(situation)

        await machine.check_access_decide(caller, action, action.Params())

        assert exporter.decision_events() == expected

    async def test_asking_in_advance_never_announces_a_run(
        self, machine: ActionProductMachine, exporter: InMemoryExporter
    ) -> None:
        """A question runs nothing: no start, no finish, whatever the answer."""
        for behaviour in _BEHAVIOURS:
            _set_object_behaviour(behaviour)

            await machine.check_access_decide(_admin(), ObjectCheckedAction, ObjectCheckedAction.Params())

        assert _RUN_START not in exporter.decision_events()
        assert _RUN_FINISH not in exporter.decision_events()


class TestOneFailedGateEvent:
    @pytest.mark.parametrize("situation", ["roles could not tell", "guard could not tell", "object could not tell"])
    async def test_exactly_one_while_executing(
        self, machine: ActionProductMachine, exporter: InMemoryExporter, situation: str
    ) -> None:
        _aim_object_check(situation)
        action, caller = _case(situation)

        await _execute(machine, action, caller, stops=True)

        assert exporter.decision_events().count(_FAILED) == 1

    @pytest.mark.parametrize("situation", ["roles could not tell", "guard could not tell", "object could not tell"])
    async def test_none_while_asking(
        self, machine: ActionProductMachine, exporter: InMemoryExporter, situation: str
    ) -> None:
        _aim_object_check(situation)
        action, caller = _case(situation)

        await machine.check_access_decide(caller, action, action.Params())

        assert _FAILED not in exporter.decision_events()

    @pytest.mark.parametrize(
        ("situation", "gate"),
        [
            ("roles could not tell", "CHECK_ROLES"),
            ("guard could not tell", "GUARD"),
            ("object could not tell", "ACCESS_DECIDE"),
        ],
    )
    async def test_it_names_the_step_and_the_kind_of_failure(
        self, machine: ActionProductMachine, exporter: InMemoryExporter, situation: str, gate: str
    ) -> None:
        _aim_object_check(situation)
        action, caller = _case(situation)

        await _execute(machine, action, caller, stops=True)

        (record,) = [one for one in exporter.records if one.name == _FAILED]
        assert record.payload["gate"] == gate
        assert record.payload["exception_type"] == "ConnectionError"


class TestTheRequestIdentity:
    async def test_it_is_carried_when_the_context_has_one(
        self, machine: ActionProductMachine, exporter: InMemoryExporter
    ) -> None:
        await _execute(machine, ConditionFailsAction, _admin(trace_id="trace-1"), stops=True)

        assert exporter.records
        assert {record.trace_id for record in exporter.records} == {"trace-1"}

    async def test_it_is_absent_when_the_context_has_none(
        self, machine: ActionProductMachine, exporter: InMemoryExporter
    ) -> None:
        await _execute(machine, ConditionFailsAction, _admin(), stops=True)

        assert exporter.records
        assert {record.trace_id for record in exporter.records} == {None}

    async def test_it_is_absent_on_the_question_path_too(
        self, machine: ActionProductMachine, exporter: InMemoryExporter
    ) -> None:
        await machine.check_access_decide(_admin(), ObjectCheckedAction, ObjectCheckedAction.Params())

        assert exporter.records
        assert {record.trace_id for record in exporter.records} == {None}


class TestNoFailureText:
    async def test_no_attribute_of_any_event_carries_it(
        self, machine: ActionProductMachine, exporter: InMemoryExporter
    ) -> None:
        _set_object_behaviour("failed")

        await _execute(machine, ObjectCheckedAction, _admin(), stops=True)

        assert exporter.records
        for record in exporter.records:
            assert _SECRET not in record.text
            assert _SECRET not in str(record.payload)

    async def test_the_failure_of_an_early_gate_stays_out_too(
        self, machine: ActionProductMachine, exporter: InMemoryExporter
    ) -> None:
        await _execute(machine, ConditionFailsAction, _admin(), stops=True)

        assert exporter.records
        for record in exporter.records:
            assert _SECRET not in record.text
            assert _SECRET not in str(record.payload)

    async def test_the_answer_carries_it_nowhere_either(self, machine: ActionProductMachine) -> None:
        verdict = await machine.check_access_decide(_admin(), GuardFailsAction, GuardFailsAction.Params())

        assert _SECRET not in str(verdict.model_dump())
