# packages/aoa-action-machine/tests/action_machine/intents/check_roles/test_reason_validation.py
"""
The rules a declared reason lives by: a condition explains itself, and the text is the
developer's — the framework invents none (FR-010, FR-012).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A refusal carries the gate that refused and, whenever a condition decided it, the reason
the developer wrote beside that condition. A condition and its reason are declared
together, and every way of declaring them apart is refused while the capability is being
declared rather than while a caller is being judged:

- a condition with no reason — the caller would have to guess why the operation refused,
  which is what the answer exists to prevent;
- a reason with nothing to explain — there is no rule whose refusal it could describe;
- a blank or non-textual reason — an answer refuses to carry one, so saying so at
  declaration time beats a surprise at the first refusal.

Where no condition decided the refusal — no listed role held, or an object answer the
developer chose to keep silent — the answer carries the gate alone, because the framework
invents no text of its own.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestAConditionExplainsItself — a condition without a reason, and a reason without a
                               condition, are both refused at declaration time
TestWhatIsUsableText         — blank and non-textual reasons are refused
TestDeclaredReasonsTravel    — a declared reason reaches the refusal unchanged
TestWhereNothingDecided      — no condition decided it, so the word stands alone
TestAConditionIsSynchronous  — async conditions are refused at declaration time
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import AccessConditionAsyncError
from aoa.action_machine.intents.access_control import Allowed, Gate, Refused, Undecided, decide
from aoa.action_machine.intents.check_roles import check_roles, grant
from aoa.action_machine.intents.check_roles.check_roles_intent_resolver import CheckRolesIntentResolver
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

from ....support.domain_model.domains import SystemDomain
from ....support.domain_model.roles import AdminRole, ManagerRole

_BOX = cast("ToolsBox", object())
"""The steps are handed a box; the probes below never read it."""
_CONNECTIONS: dict[str, BaseResource] = {}


def _is_sales_agent(user: Any) -> bool:
    """A condition that only one caller satisfies."""
    return user.user_id == "sales"


def _always_refuses(user: Any, params: Any) -> bool:
    """A shared condition that refuses everyone."""
    return False


async def _async_when(user: Any) -> bool:
    """A condition the synchronous step cannot evaluate."""
    return True


async def _async_guard(user: Any, params: Any) -> bool:
    """A shared condition the synchronous step cannot evaluate."""
    return True


def _refuses_first(user: Any) -> bool:
    """One way in, refusing."""
    return False


def _refuses_second(user: Any) -> bool:
    """Another way in, refusing too."""
    return False


@meta(description="reasons: two ways in for one role, both refused", domain=SystemDomain)
@check_roles(
    grant(ManagerRole, when=_refuses_first, reason="FIRST_WAY_IN"),
    grant(ManagerRole, when=_refuses_second, reason="SECOND_WAY_IN"),
)
class TwoWaysRefusedAction(BaseAction["TwoWaysRefusedAction.Params", "TwoWaysRefusedAction.Result"]):
    """An operation whose two matching grants refuse, each with its own reason."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


@meta(description="reasons: a grant that explains why it refuses", domain=SystemDomain)
@check_roles(grant(ManagerRole, when=_is_sales_agent, reason="ONLY_SALES_AGENTS"))
class DeclaredWhenReasonAction(BaseAction["DeclaredWhenReasonAction.Params", "DeclaredWhenReasonAction.Result"]):
    """An operation whose role condition explains itself."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


@meta(description="reasons: a shared condition that explains why it refuses", domain=SystemDomain)
@check_roles(AdminRole, guard=_always_refuses, guard_reason="SHOP_CLOSED")
class DeclaredGuardReasonAction(BaseAction["DeclaredGuardReasonAction.Params", "DeclaredGuardReasonAction.Result"]):
    """An operation whose shared condition explains itself."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


@meta(description="reasons: an operation with no condition at all", domain=SystemDomain)
@check_roles(AdminRole)
class NoConditionAction(BaseAction["NoConditionAction.Params", "NoConditionAction.Result"]):
    """An operation that lists a role and declares no condition."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


def _manager_who_is_not_sales() -> Context:
    """A caller holding the role, without the user identity its condition asks for."""
    return Context(user=UserInfo(user_id="not-sales", roles=(ManagerRole,)))


def _admin() -> Context:
    """A caller holding the role the shared-condition probes list."""
    return Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))


def _nobody() -> Context:
    """A caller holding none of the listed roles."""
    return Context(user=UserInfo(user_id="n1", roles=()))


async def _ask(action: BaseAction[Any, Any], caller: Context) -> Any:
    """Ask in advance about one call, through the real steps."""
    return await decide(caller, action, action.Params(), _BOX, _CONNECTIONS)


class TestAConditionExplainsItself:
    def test_a_role_condition_without_a_reason_is_refused(self) -> None:
        with pytest.raises(ValueError, match="reason"):
            grant(ManagerRole, when=_is_sales_agent)

    def test_a_shared_condition_without_a_reason_is_refused(self) -> None:
        with pytest.raises(ValueError, match="guard_reason"):
            check_roles(AdminRole, guard=_always_refuses)

    def test_a_reason_without_a_condition_is_refused(self) -> None:
        with pytest.raises(ValueError, match="reason"):
            grant(AdminRole, reason="NOTHING_TO_EXPLAIN")

    def test_a_guard_reason_without_a_guard_is_refused(self) -> None:
        with pytest.raises(ValueError, match="guard_reason"):
            check_roles(AdminRole, guard_reason="NOTHING_TO_EXPLAIN")

    def test_a_condition_with_its_reason_is_kept(self) -> None:
        built = grant(ManagerRole, when=_is_sales_agent, reason="ONLY_SALES_AGENTS")

        assert built.reason == "ONLY_SALES_AGENTS"

    def test_a_declaration_with_no_condition_needs_no_reason(self) -> None:
        """Nothing refuses by condition here, so there is nothing to explain."""
        built = grant(AdminRole)

        assert built.when is None
        assert built.reason is None


class TestWhatIsUsableText:
    def test_a_blank_reason_is_refused(self) -> None:
        """A reason is text a caller reads; blank is not text."""
        with pytest.raises(ValueError, match="reason"):
            grant(ManagerRole, when=_is_sales_agent, reason="   ")

    def test_a_reason_that_is_not_text_is_refused(self) -> None:
        with pytest.raises(TypeError, match="reason"):
            grant(ManagerRole, when=_is_sales_agent, reason=42)  # type: ignore[arg-type]


class TestDeclaredReasonsTravel:
    async def test_a_declared_role_reason_reaches_the_refusal(self) -> None:
        answer = await _ask(DeclaredWhenReasonAction(), _manager_who_is_not_sales())

        assert isinstance(answer, Refused)
        assert answer.gate is Gate.WHEN
        assert answer.reason == "ONLY_SALES_AGENTS"

    async def test_a_declared_shared_reason_reaches_the_refusal(self) -> None:
        answer = await _ask(DeclaredGuardReasonAction(), _admin())

        assert isinstance(answer, Refused)
        assert answer.gate is Gate.GUARD
        assert answer.reason == "SHOP_CLOSED"

    def test_the_declaration_carries_the_shared_reason(self) -> None:
        assert CheckRolesIntentResolver.resolve_guard_reason(DeclaredGuardReasonAction) == "SHOP_CLOSED"

    def test_the_declaration_carries_the_role_reason(self) -> None:
        grants = CheckRolesIntentResolver.resolve_grants(DeclaredWhenReasonAction)

        assert [one.reason for one in grants] == ["ONLY_SALES_AGENTS"]

    async def test_several_matching_conditions_report_the_first_declared_reason(self) -> None:
        """Declaration order is the order of the ways in, so the first refusal is the answer."""
        answer = await _ask(TwoWaysRefusedAction(), _manager_who_is_not_sales())

        assert isinstance(answer, Refused)
        assert answer.gate is Gate.WHEN
        assert answer.reason == "FIRST_WAY_IN"

    async def test_a_caller_the_condition_admits_is_allowed(self) -> None:
        caller = Context(user=UserInfo(user_id="sales", roles=(ManagerRole,)))

        assert isinstance(await _ask(DeclaredWhenReasonAction(), caller), Allowed)

    async def test_an_operation_with_no_condition_is_allowed(self) -> None:
        assert isinstance(await _ask(NoConditionAction(), _admin()), Allowed)


class TestWhereNothingDecided:
    async def test_no_listed_role_held_answers_with_the_word_alone(self) -> None:
        """No condition refused here — the role was never held — so nothing is explained."""
        answer = await _ask(DeclaredWhenReasonAction(), _nobody())

        assert isinstance(answer, Refused)
        assert answer.gate is Gate.CHECK_ROLES
        assert answer.reason is None

    async def test_the_answer_carries_no_text_beyond_the_gate(self) -> None:
        answer = await _ask(DeclaredWhenReasonAction(), _nobody())

        assert answer.model_dump() == {"kind": "refused", "gate": Gate.CHECK_ROLES, "reason": None}


class TestAConditionIsSynchronous:
    def test_an_async_role_condition_is_refused_at_declaration(self) -> None:
        class Probe:
            """A class about to receive a declaration the engine cannot evaluate."""

        with pytest.raises(AccessConditionAsyncError):
            check_roles(grant(AdminRole, when=_async_when, reason="ASYNC_NEVER"))(Probe)

    def test_an_async_shared_condition_is_refused_at_declaration(self) -> None:
        class Probe:
            """A class about to receive a declaration the engine cannot evaluate."""

        with pytest.raises(AccessConditionAsyncError):
            check_roles(AdminRole, guard=_async_guard, guard_reason="ASYNC_GUARD")(Probe)

    async def test_no_such_declaration_is_ever_asked(self) -> None:
        """The point of refusing early: a step never receives a condition it cannot call."""
        answer = await _ask(DeclaredWhenReasonAction(), _manager_who_is_not_sales())

        assert isinstance(answer, Refused | Undecided)
