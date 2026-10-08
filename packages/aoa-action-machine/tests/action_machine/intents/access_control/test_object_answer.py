# packages/aoa-action-machine/tests/action_machine/intents/access_control/test_object_answer.py
"""
An object-scoped refusal tells the caller nothing about the object (FR-011, SC-003).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

"there is no such object" and "that object belongs to someone else" must be one answer,
not two. Told apart, they turn the access check into an oracle: ask about any identifier
and learn whether it exists, without ever being allowed to touch it.

The engine's part is to carry the developer's single answer unchanged — so this module
samples pairs of the two situations and demands that each pair is identical in word,
gate and reason, on both paths, and that neither answer carries the object's identity.

The probe below models the pattern the developer surface recommends: one branch, and
``FORBIDDEN_OBJECT`` as its answer.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestSampledPairsAgree       — ten sampled pairs, word, gate and reason identical
TestTheExecutionPathAgrees  — the same call executed, stopped the same way
TestNothingLeaks            — no identifier, no text, and an allowed call still differs
"""

from __future__ import annotations

import random

import pytest
from pydantic import Field

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AuthorizationError
from aoa.action_machine.intents.access_control import FORBIDDEN_OBJECT, Allowed, Gate, Refused, Verdict
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.action_product_machine import ActionProductMachine
from aoa.action_machine.runtime.tools_box import ToolsBox

from ....support.domain_model.domains import SystemDomain
from ....support.domain_model.roles import AdminRole

_CALLER = "the-caller"
_OTHER = "someone-else"

_OBJECTS: dict[str, str] = {}
"""What the probe's store holds: object id → its owner."""


@meta(description="object answers: the call is about an object the caller must own", domain=SystemDomain)
@check_roles(AdminRole)
class ObjectScopedAction(BaseAction["ObjectScopedAction.Params", "ObjectScopedAction.Result"]):
    """An operation whose check refuses a missing object and a foreign one by one branch."""

    class Params(BaseParams):
        """The object the call is about."""

        object_id: str = Field(default="", description="Identifier of the object")

    class Result(BaseResult):
        """No outputs."""

    @access_decide
    async def object_scoped_access_decide(
        self,
        params: ObjectScopedAction.Params,
        context: Context,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> Verdict:
        """One branch for both situations: no such object, and somebody else's object."""
        owner = _OBJECTS.get(params.object_id)
        if owner is None or owner != context.user.user_id:
            return FORBIDDEN_OBJECT
        return Allowed()


def _caller() -> Context:
    """The caller the probe's own objects belong to."""
    return Context(user=UserInfo(user_id=_CALLER, roles=(AdminRole,)))


def _machine() -> ActionProductMachine:
    """A machine without a cache."""
    return ActionProductMachine(cache_coordinator=None)


def _sampled_pairs(count: int = 10) -> list[tuple[str, str]]:
    """Return ``count`` pairs of a missing identifier and a foreign one, deterministically."""
    rng = random.Random(20261008)
    pairs: list[tuple[str, str]] = []
    for index in range(count):
        missing = f"ORD-absent-{rng.randint(10**6, 10**7)}"
        foreign = f"ORD-foreign-{index}-{rng.randint(10**6, 10**7)}"
        _OBJECTS[foreign] = _OTHER
        pairs.append((missing, foreign))
    return pairs


_PAIRS = _sampled_pairs()


@pytest.fixture
def machine() -> ActionProductMachine:
    """A machine that answers questions and runs calls."""
    return _machine()


class TestSampledPairsAgree:
    @pytest.mark.parametrize(("missing_id", "foreign_id"), _PAIRS, ids=lambda value: value if isinstance(value, str) else "")
    async def test_a_missing_object_and_a_foreign_one_are_the_same_answer(
        self, machine: ActionProductMachine, missing_id: str, foreign_id: str
    ) -> None:
        absent = await machine.check_access_decide(
            _caller(), ObjectScopedAction, ObjectScopedAction.Params(object_id=missing_id)
        )
        foreign = await machine.check_access_decide(
            _caller(), ObjectScopedAction, ObjectScopedAction.Params(object_id=foreign_id)
        )

        assert isinstance(absent, Refused)
        assert isinstance(foreign, Refused)
        assert absent == foreign

    @pytest.mark.parametrize(("missing_id", "foreign_id"), _PAIRS[:3], ids=lambda value: value if isinstance(value, str) else "")
    async def test_the_word_the_gate_and_the_reason_are_identical(
        self, machine: ActionProductMachine, missing_id: str, foreign_id: str
    ) -> None:
        absent = await machine.check_access_decide(
            _caller(), ObjectScopedAction, ObjectScopedAction.Params(object_id=missing_id)
        )
        foreign = await machine.check_access_decide(
            _caller(), ObjectScopedAction, ObjectScopedAction.Params(object_id=foreign_id)
        )

        assert isinstance(absent, Refused) and isinstance(foreign, Refused)
        assert absent.kind == foreign.kind == "refused"
        assert absent.gate is foreign.gate is Gate.ACCESS_DECIDE
        assert absent.reason == foreign.reason is None


class TestTheExecutionPathAgrees:
    @pytest.mark.parametrize(("missing_id", "foreign_id"), _PAIRS[:3], ids=lambda value: value if isinstance(value, str) else "")
    async def test_executing_both_stops_the_call_the_same_way(
        self, machine: ActionProductMachine, missing_id: str, foreign_id: str
    ) -> None:
        with pytest.raises(AuthorizationError) as absent_exc:
            await machine.run(_caller(), ObjectScopedAction(), ObjectScopedAction.Params(object_id=missing_id))
        with pytest.raises(AuthorizationError) as foreign_exc:
            await machine.run(_caller(), ObjectScopedAction(), ObjectScopedAction.Params(object_id=foreign_id))

        assert str(absent_exc.value) == str(foreign_exc.value)
        assert absent_exc.value.level == foreign_exc.value.level


class TestNothingLeaks:
    @pytest.mark.parametrize(("missing_id", "foreign_id"), _PAIRS[:3], ids=lambda value: value if isinstance(value, str) else "")
    async def test_the_answer_carries_no_identifier_and_no_text(
        self, machine: ActionProductMachine, missing_id: str, foreign_id: str
    ) -> None:
        for object_id in (missing_id, foreign_id):
            answer = await machine.check_access_decide(
                _caller(), ObjectScopedAction, ObjectScopedAction.Params(object_id=object_id)
            )

            assert object_id not in str(answer.model_dump())

    async def test_an_object_the_caller_owns_is_still_allowed(self, machine: ActionProductMachine) -> None:
        """The guard against a vacuous test: the same check does answer ``allowed``."""
        own_id = "ORD-own-1"
        _OBJECTS[own_id] = _CALLER

        answer = await machine.check_access_decide(
            _caller(), ObjectScopedAction, ObjectScopedAction.Params(object_id=own_id)
        )

        assert isinstance(answer, Allowed)
