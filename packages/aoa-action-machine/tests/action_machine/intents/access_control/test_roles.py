# tests/action_machine/intents/access_control/test_roles.py
"""Unit tests for ``RoleChecker`` — it answers, and the cascade asks it.

The checker no longer raises for a decision: it returns ``Refused`` naming
``CHECK_ROLES`` or ``WHEN``, and ``None`` when the caller may continue. It reads the
declaration (the grants ``@check_roles`` wrote) rather than the assembled graph, so
these tests hand it an action class. The shared ``guard=`` moved to the cascade's own
step, so it is exercised through ``guard_answer`` here.
"""

from __future__ import annotations

import pytest
from pydantic import Field

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.application_role import ApplicationRole
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.context.context import Context
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.exceptions import MissingCheckRolesError
from aoa.action_machine.intents.access_control import Gate, Refused
from aoa.action_machine.intents.access_control.cascade import guard_answer
from aoa.action_machine.intents.access_control.roles import RoleChecker
from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from aoa.action_machine.intents.check_roles import check_roles, grant
from aoa.action_machine.intents.meta.meta_decorator import meta
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode, role_mode
from aoa.action_machine.model.base_action import BaseAction
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_result import BaseResult
from aoa.action_machine.model.base_state import BaseState
from aoa.action_machine.resources.base_resource import BaseResource
from aoa.action_machine.runtime.tools_box import ToolsBox

from ....action_machine.scenarios.intents_with_runtime.test_role_checker_pr2 import OrderManagerRole, OrderViewerRole
from ....support.domain_model.admin_action import AdminAction
from ....support.domain_model.domains import SystemDomain
from ....support.domain_model.ping_action import PingAction
from ....support.domain_model.roles import AdminRole, EditorRole, ManagerRole, SpyRole, UserRole


def test_ping_none_role_allows_anonymous_context() -> None:
    checker = RoleChecker()
    assert checker.check(Context(), PingAction) is None


def test_admin_answered_check_roles_without_the_role() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u1", roles=(UserRole,)))
    answer = checker.check(ctx, AdminAction)
    assert isinstance(answer, Refused)
    assert answer.gate is Gate.CHECK_ROLES


def test_admin_allowed_with_matching_role() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))
    assert checker.check(ctx, AdminAction) is None


@meta(description="OR semantics for RoleChecker", domain=SystemDomain)
@check_roles([EditorRole, SpyRole])
class OrRolesProbeAction(BaseAction["OrRolesProbeAction.Params", "OrRolesProbeAction.Result"]):
    class Params(BaseParams):
        dummy: str = Field(default="x", description="Probe param")

    class Result(BaseResult):
        ok: bool = Field(description="Probe result")

    @summary_aspect("Summary")
    async def or_roles_summary(
        self,
        params: OrRolesProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> OrRolesProbeAction.Result:
        return OrRolesProbeAction.Result(ok=True)


def test_or_roles_one_alternative_matches() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="s1", roles=(SpyRole,)))
    assert checker.check(ctx, OrRolesProbeAction) is None


def test_or_roles_none_match() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u1", roles=(UserRole,)))
    answer = checker.check(ctx, OrRolesProbeAction)
    assert isinstance(answer, Refused)
    assert answer.gate is Gate.CHECK_ROLES


@meta(description="AnyRole sentinel", domain=SystemDomain)
@check_roles(AnyRole)
class AnyRoleProbeAction(BaseAction["AnyRoleProbeAction.Params", "AnyRoleProbeAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(description="ok")

    @summary_aspect("S")
    async def any_probe_summary(
        self,
        params: AnyRoleProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> AnyRoleProbeAction.Result:
        return AnyRoleProbeAction.Result(ok=True)


def test_any_role_requires_at_least_one_active_role() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="anon", roles=()))
    answer = checker.check(ctx, AnyRoleProbeAction)
    assert isinstance(answer, Refused)
    assert answer.gate is Gate.CHECK_ROLES


def test_any_role_allows_registered_role() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u", roles=(UserRole,)))
    assert checker.check(ctx, AnyRoleProbeAction) is None


@meta(description="Subclass role suffices for base-role requirement", domain=SystemDomain)
@check_roles(OrderViewerRole)
class HierarchyRoleProbeAction(BaseAction["HierarchyRoleProbeAction.Params", "HierarchyRoleProbeAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(description="ok")

    @summary_aspect("S")
    async def hierarchy_probe_summary(
        self,
        params: HierarchyRoleProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> HierarchyRoleProbeAction.Result:
        return HierarchyRoleProbeAction.Result(ok=True)


def test_required_base_role_met_by_strict_subclass_user() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="m", roles=(OrderManagerRole,)))
    assert checker.check(ctx, HierarchyRoleProbeAction) is None


@role_mode(RoleMode.SILENCED)
class SilencedRole(ApplicationRole):
    name = "silenced"
    description = "Filtered from active role checks"


def test_silenced_roles_dropped_before_match() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u", roles=(SilencedRole, AdminRole)))
    assert checker.check(ctx, AdminAction) is None


def test_only_silenced_roles_fail_admin() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u", roles=(SilencedRole,)))
    answer = checker.check(ctx, AdminAction)
    assert isinstance(answer, Refused)
    assert answer.gate is Gate.CHECK_ROLES


def test_check_raises_when_the_action_declares_no_roles() -> None:
    """A declaration the checker cannot read is a build-time mistake, not an answer."""

    class UndeclaredProbe:
        """A class with no ``@check_roles`` declaration at all."""

    with pytest.raises(MissingCheckRolesError, match="@check_roles"):
        RoleChecker().check(Context(), UndeclaredProbe)  # type: ignore[arg-type]


class _BrokenRoleChecker(RoleChecker):
    """Forces the defensive fallback on a spec the checker cannot make sense of."""

    @staticmethod
    def _spec_from_grants(grants: list[object]) -> object:
        _ = grants
        return object()


def test_check_invalid_reconstructed_spec_type_error() -> None:
    ctx = Context(user=UserInfo(user_id="u", roles=(AdminRole,)))
    with pytest.raises(TypeError, match="Invalid reconstructed"):
        _BrokenRoleChecker().check(ctx, PingAction)


def _is_sales_agent(user) -> bool:
    return user.user_id == "sales_agent"


def _order_not_archived(user, params) -> bool:
    return not params.order_id.startswith("ARCHIVED-")


@meta(description="grant()/guard= probe for RoleChecker level 2", domain=SystemDomain)
@check_roles(
    grant(AdminRole),
    grant(ManagerRole, when=_is_sales_agent),
    guard=_order_not_archived,
)
class GrantGuardProbeAction(BaseAction["GrantGuardProbeAction.Params", "GrantGuardProbeAction.Result"]):
    class Params(BaseParams):
        order_id: str = Field(default="ORD-1")

    class Result(BaseResult):
        ok: bool = Field(description="ok")

    @summary_aspect("S")
    async def probe_summary(
        self,
        params: GrantGuardProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GrantGuardProbeAction.Result:
        return GrantGuardProbeAction.Result(ok=True)


def test_denied_without_any_role_match_answers_check_roles() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u1", roles=(UserRole,)))
    answer = checker.check(ctx, GrantGuardProbeAction, GrantGuardProbeAction.Params())
    assert isinstance(answer, Refused)
    assert answer.gate is Gate.CHECK_ROLES


def test_bare_grant_matches_unconditionally() -> None:
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))
    assert checker.check(ctx, GrantGuardProbeAction, GrantGuardProbeAction.Params()) is None


def test_grant_when_false_answers_when() -> None:
    """ManagerRole matches structurally, but when= rejects (wrong user_id); no other
    grant matches a ManagerRole-only user, so the word is WHEN, not CHECK_ROLES."""
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="not_sales", roles=(ManagerRole,)))
    answer = checker.check(ctx, GrantGuardProbeAction, GrantGuardProbeAction.Params())
    assert isinstance(answer, Refused)
    assert answer.gate is Gate.WHEN


def test_grant_when_true_allows_a_later_grant_to_win() -> None:
    """The first grant (AdminRole, unconditional) does not match this user — the second
    grant (ManagerRole + when=) is tried next and wins. Proves any()/declaration order."""
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="sales_agent", roles=(ManagerRole,)))
    assert checker.check(ctx, GrantGuardProbeAction, GrantGuardProbeAction.Params()) is None


def test_the_guard_answers_guard_when_it_refuses() -> None:
    """The shared condition is a step of its own, so its refusal is its own word."""
    ctx = Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))
    answer = guard_answer(ctx, GrantGuardProbeAction(), GrantGuardProbeAction.Params(order_id="ARCHIVED-1"))
    assert isinstance(answer, Refused)
    assert answer.gate is Gate.GUARD


def test_check_without_params_still_works() -> None:
    """Roles alone need no parameters: the shared condition is a different step."""
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="a1", roles=(AdminRole,)))
    assert checker.check(ctx, AdminAction) is None


def _always_false(user) -> bool:
    return False


@meta(description="GuestRole grant with its own when= probe", domain=SystemDomain)
@check_roles(grant(GuestRole, when=_always_false))
class GuestWhenProbeAction(BaseAction["GuestWhenProbeAction.Params", "GuestWhenProbeAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(description="ok")

    @summary_aspect("S")
    async def probe_summary(
        self,
        params: GuestWhenProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> GuestWhenProbeAction.Result:
        return GuestWhenProbeAction.Result(ok=True)


def test_guest_role_grant_when_false_answers_when() -> None:
    """Regression: `grant(GuestRole, when=...)` is a valid declaration (GuestRole is an
    ordinary BaseRole subclass as far as grant() is concerned) — its when= must not be
    silently ignored just because GuestRole normally bypasses role matching entirely."""
    checker = RoleChecker()
    answer = checker.check(Context(), GuestWhenProbeAction)
    assert isinstance(answer, Refused)
    assert answer.gate is Gate.WHEN


@meta(description="AnyRole grant with its own when= probe", domain=SystemDomain)
@check_roles(grant(AnyRole, when=_always_false))
class AnyWhenProbeAction(BaseAction["AnyWhenProbeAction.Params", "AnyWhenProbeAction.Result"]):
    class Params(BaseParams):
        pass

    class Result(BaseResult):
        ok: bool = Field(description="ok")

    @summary_aspect("S")
    async def probe_summary(
        self,
        params: AnyWhenProbeAction.Params,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResource],
    ) -> AnyWhenProbeAction.Result:
        return AnyWhenProbeAction.Result(ok=True)


def test_any_role_grant_when_false_answers_when() -> None:
    """Same regression as above, for AnyRole: at least one active role is present
    (AnyRole's own gate passes), but the grant's own when= must still be honored."""
    checker = RoleChecker()
    ctx = Context(user=UserInfo(user_id="u", roles=(UserRole,)))
    answer = checker.check(ctx, AnyWhenProbeAction)
    assert isinstance(answer, Refused)
    assert answer.gate is Gate.WHEN
