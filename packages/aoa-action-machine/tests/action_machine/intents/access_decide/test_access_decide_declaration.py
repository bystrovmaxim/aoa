# packages/aoa-action-machine/tests/action_machine/intents/access_decide/test_access_decide_declaration.py
"""
Tests for the declared object check — the rules that hold at declaration time.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Pin the three rules that come with declaring an object check (FR-019): a check is
declared and found; declaring none is legitimate; and there is at most one per
operation, never inherited, named with the required suffix, asynchronous and with
the arity the engine calls it with.

═══════════════════════════════════════════════════════════════════════════════
STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

TestDeclaredCheck        — a declared check is found, and the operation is marked
TestNoDeclaration        — an operation that declares none simply has none
TestAtMostOne            — a second declaration is refused
TestWhatADeclarationMustLookLike — suffix, async, arity
TestNotInherited         — a subclass never answers with its parent's check
"""

from __future__ import annotations

from typing import Any

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.exceptions import DuplicateAccessDecideError, NamingSuffixError
from aoa.action_machine.intents.access_control import Allowed
from aoa.action_machine.intents.access_decide import access_decide
from aoa.action_machine.intents.access_decide.access_decide_intent_resolver import AccessDecideIntentResolver
from aoa.action_machine.intents.check_roles import check_roles
from aoa.action_machine.intents.context_requires import context_requires
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.runtime.tools_box import ToolsBox

from ....support.domain_model.domains import SystemDomain
from ....support.domain_model.roles import AdminRole


@meta(description="declaration: an operation that declares an object check", domain=SystemDomain)
@check_roles(AdminRole)
class DeclaringAction(BaseAction["DeclaringAction.Params", "DeclaringAction.Result"]):
    """An operation whose object check is declared."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide
    async def declaring_access_decide(
        self,
        params: DeclaringAction.Params,
        context: Context,
        box: ToolsBox,
        connections: dict[str, Any],
    ) -> Allowed:
        """Answer that the object may be touched."""
        return Allowed()


@meta(description="declaration: an operation that declares nothing", domain=SystemDomain)
@check_roles(AdminRole)
class SilentAction(BaseAction["SilentAction.Params", "SilentAction.Result"]):
    """An operation with no object check at all — a legitimate choice."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""


@meta(description="declaration: a subclass that declares nothing", domain=SystemDomain)
@check_roles(AdminRole)
class InheritingAction(DeclaringAction):
    """A subclass that declares no check of its own."""


@meta(description="declaration: a subclass that declares its own check", domain=SystemDomain)
@check_roles(AdminRole)
class OwnCheckAction(DeclaringAction):
    """A subclass whose own declaration must win over its parent's."""

    class Params(BaseParams):
        """No inputs."""

    class Result(BaseResult):
        """No outputs."""

    @access_decide
    async def own_check_access_decide(
        self,
        params: OwnCheckAction.Params,
        context: Context,
        box: ToolsBox,
        connections: dict[str, Any],
    ) -> Allowed:
        """Answer with this subclass's own decision."""
        return Allowed()


def _declared_check(name: str) -> Any:
    """Build a well-formed check carrying the given name, declared and marked."""
    async def check(self: Any, params: Any, context: Any, box: Any, connections: Any) -> Allowed:
        return Allowed()

    check.__name__ = name
    return access_decide(check)


class TestDeclaredCheck:
    def test_a_declared_check_is_found(self) -> None:
        resolved = AccessDecideIntentResolver.resolve_check(DeclaringAction)
        assert resolved is not None
        assert resolved.__name__ == "declaring_access_decide"

    def test_the_operation_is_marked_as_declaring(self) -> None:
        assert AccessDecideIntentResolver.is_declared(DeclaringAction) is True

    def test_the_resolved_callable_is_the_declared_one(self) -> None:
        resolved = AccessDecideIntentResolver.resolve_check(DeclaringAction)
        assert resolved is DeclaringAction.__dict__["declaring_access_decide"]


class TestNoDeclaration:
    def test_an_operation_without_a_check_resolves_to_nothing(self) -> None:
        assert AccessDecideIntentResolver.resolve_check(SilentAction) is None

    def test_an_operation_without_a_check_is_not_marked(self) -> None:
        assert AccessDecideIntentResolver.is_declared(SilentAction) is False

    def test_declaring_nothing_is_legal(self) -> None:
        assert issubclass(SilentAction, BaseAction)


class TestAtMostOne:
    def test_a_second_declaration_is_refused(self) -> None:
        class TwoChecks:
            """A class carrying two marked checks — the resolver must refuse to choose."""

            first_access_decide = _declared_check("first_access_decide")
            second_access_decide = _declared_check("second_access_decide")

        with pytest.raises(DuplicateAccessDecideError, match="more than one object check"):
            AccessDecideIntentResolver.resolve_check(TwoChecks)

    def test_the_refusal_names_both_declarations(self) -> None:
        class TwoChecks:
            """Two marked checks, so the operator can see which two collided."""

            first_access_decide = _declared_check("first_access_decide")
            second_access_decide = _declared_check("second_access_decide")

        with pytest.raises(DuplicateAccessDecideError) as caught:
            AccessDecideIntentResolver.resolve_check(TwoChecks)

        assert "first_access_decide" in str(caught.value)
        assert "second_access_decide" in str(caught.value)

    def test_one_declaration_is_not_a_duplicate(self) -> None:
        class OneCheck:
            """Exactly one marked check."""

            only_access_decide = _declared_check("only_access_decide")

        assert AccessDecideIntentResolver.is_declared(OneCheck) is True


class TestWhatADeclarationMustLookLike:
    async def test_a_name_without_the_suffix_is_refused(self) -> None:
        async def badly_named(self: Any, params: Any, context: Any, box: Any, connections: Any) -> Allowed:
            return Allowed()

        with pytest.raises(NamingSuffixError, match="_access_decide"):
            access_decide(badly_named)

    def test_a_synchronous_check_is_refused(self) -> None:
        def sync_named(self: Any, params: Any, context: Any, box: Any, connections: Any) -> Allowed:
            return Allowed()

        sync_named.__name__ = "sync_named_access_decide"

        with pytest.raises(TypeError, match="must be async"):
            access_decide(sync_named)

    async def test_a_check_with_the_wrong_arity_is_refused(self) -> None:
        async def too_few(self: Any, params: Any) -> Allowed:
            return Allowed()

        too_few.__name__ = "too_few_access_decide"

        with pytest.raises(TypeError, match="must accept 5 parameters"):
            access_decide(too_few)

    async def test_the_arity_context_requires_produces_is_accepted(self) -> None:
        @context_requires("user.user_id")
        async def with_ctx(
            self: Any, params: Any, context: Any, box: Any, connections: Any, ctx: Any
        ) -> Allowed:
            return Allowed()

        with_ctx.__name__ = "with_ctx_access_decide"

        assert access_decide(with_ctx).__name__ == "with_ctx_access_decide"


class TestNotInherited:
    def test_a_subclass_does_not_inherit_its_parent_check(self) -> None:
        assert AccessDecideIntentResolver.resolve_check(InheritingAction) is None

    def test_a_subclass_is_not_marked_by_its_parent(self) -> None:
        assert AccessDecideIntentResolver.is_declared(InheritingAction) is False

    def test_a_subclass_that_declares_its_own_check_is_answered_by_it(self) -> None:
        resolved = AccessDecideIntentResolver.resolve_check(OwnCheckAction)
        assert resolved is not None
        assert resolved.__name__ == "own_check_access_decide"

    def test_the_parent_still_answers_with_its_own(self) -> None:
        resolved = AccessDecideIntentResolver.resolve_check(DeclaringAction)
        assert resolved is not None
        assert resolved.__name__ == "declaring_access_decide"

    def test_a_grandchild_inherits_from_neither(self) -> None:
        @meta(description="declaration: a grandchild that declares nothing", domain=SystemDomain)
        @check_roles(AdminRole)
        class GrandchildAction(OwnCheckAction):
            """A grandchild two levels below a declaration."""

            class Params(BaseParams):
                """No inputs."""

            class Result(BaseResult):
                """No outputs."""

        assert AccessDecideIntentResolver.resolve_check(GrandchildAction) is None
