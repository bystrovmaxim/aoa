"""Golden tests for grant(...)/guard= on @check_roles (access-control-cascade steps 4 and 9)."""

from __future__ import annotations

import pytest

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.exceptions import AccessConditionAsyncError
from aoa.action_machine.intents.access_control import FailSecurityVerdict
from aoa.action_machine.intents.check_roles.check_roles_decorator import check_roles
from aoa.action_machine.intents.check_roles.grant import Grant, grant

from ....support.domain_model.roles import AdminRole, ManagerRole


def _sales_only(user: object) -> bool:
    return True


class TestGrantConstruction:
    def test_grant_stores_role_when_and_reason(self) -> None:
        reason = FailSecurityVerdict("sales only")
        g = grant(AdminRole, when=_sales_only, reason=reason)
        assert g.role is AdminRole
        assert g.when is _sales_only
        assert g.reason == reason

    def test_grant_when_and_reason_default_to_none(self) -> None:
        g = grant(AdminRole)
        assert g.when is None
        assert g.reason is None

    def test_grant_rejects_non_role(self) -> None:
        class NotRole:
            pass

        with pytest.raises(TypeError, match="BaseRole"):
            grant(NotRole)  # type: ignore[arg-type]

    def test_grant_when_without_reason_defaults_to_forbidden_grant(self) -> None:
        g = grant(AdminRole, when=_sales_only)
        assert g.reason == FailSecurityVerdict("FORBIDDEN_GRANT")

    def test_grant_reason_without_when_raises(self) -> None:
        with pytest.raises(ValueError, match=r"reason=.*when="):
            grant(AdminRole, reason=FailSecurityVerdict("sales only"))

    def test_grant_reason_as_plain_string_raises(self) -> None:
        """baseverdict-audit finding 3, third document: reason= was a plain str before the
        BaseVerdict redesign -- a caller passing an ordinary string through (migrated code,
        or simply unchecked by mypy) must be rejected at declaration, not reach a real
        AuthorizationError and crash the first time something reads .verdict.reason off it."""
        with pytest.raises(TypeError, match="FailSecurityVerdict"):
            grant(AdminRole, when=_sales_only, reason="sales only")  # type: ignore[arg-type]

    def test_grant_dataclass_constructed_directly_still_validates(self) -> None:
        """baseverdict-audit finding 1, fourth document: Grant is public and importable
        on its own -- constructing it directly, bypassing grant() entirely, must not
        skip the reason= validation that only lived in grant()'s own body before."""
        with pytest.raises(TypeError, match="FailSecurityVerdict"):
            Grant(role=AdminRole, when=_sales_only, reason="sales only")  # type: ignore[arg-type]
        with pytest.raises(ValueError, match=r"reason=.*when="):
            Grant(role=AdminRole, reason=FailSecurityVerdict("sales only"))

    def test_grant_dataclass_constructed_directly_still_defaults(self) -> None:
        """Same bypass path, the non-error half: when= alone still defaults reason=
        to FORBIDDEN_GRANT even when Grant is built without going through grant()."""
        g = Grant(role=AdminRole, when=_sales_only)
        assert g.reason == FailSecurityVerdict("FORBIDDEN_GRANT")


class TestCheckRolesGrants:
    def test_single_grant_spec_is_bare_type(self) -> None:
        @check_roles(grant(AdminRole))
        class _Action:
            pass

        assert _Action._role_info["spec"] is AdminRole
        assert _Action._role_info["grants"] == [Grant(role=AdminRole, when=None)]
        assert _Action._role_info["guard"] is None

    def test_multiple_grants_preserved_in_order(self) -> None:
        reason = FailSecurityVerdict("sales only")

        @check_roles(grant(AdminRole), grant(ManagerRole, when=_sales_only, reason=reason))
        class _Action:
            pass

        grants = _Action._role_info["grants"]
        assert len(grants) == 2
        assert grants[0] == Grant(role=AdminRole, when=None)
        assert grants[1].role is ManagerRole
        assert grants[1].when is _sales_only
        assert grants[1].reason == reason
        assert _Action._role_info["spec"] == (AdminRole, ManagerRole)

    def test_bare_role_and_grant_mixed(self) -> None:
        @check_roles(AdminRole, grant(ManagerRole, when=_sales_only, reason=FailSecurityVerdict("sales only")))
        class _Action:
            pass

        grants = _Action._role_info["grants"]
        assert len(grants) == 2
        assert grants[0] == Grant(role=AdminRole, when=None)
        assert grants[1].role is ManagerRole

    def test_bare_role_path_also_populates_grants(self) -> None:
        @check_roles(AdminRole)
        class _Action:
            pass

        assert _Action._role_info["grants"] == [Grant(role=AdminRole, when=None)]

    def test_sentinel_specs_still_get_one_grant(self) -> None:
        """GuestRole/AnyRole are BaseRole subclasses themselves — RoleGraphEdge.get_role_edges
        needs exactly one edge for them, same as any concrete role (see grant.py comment)."""

        @check_roles(GuestRole)
        class _GuestAction:
            pass

        @check_roles(AnyRole)
        class _AnyAction:
            pass

        assert _GuestAction._role_info["grants"] == [Grant(role=GuestRole, when=None)]
        assert _AnyAction._role_info["grants"] == [Grant(role=AnyRole, when=None)]


class TestCheckRolesGuard:
    def test_guard_and_reason_stored(self) -> None:
        def guard_fn(user: object, params: object) -> bool:
            return True

        reason = FailSecurityVerdict("not eligible")

        @check_roles(AdminRole, guard=guard_fn, reason=reason)
        class _Action:
            pass

        assert _Action._role_info["guard"] is guard_fn
        assert _Action._role_info["guard_reason"] == reason

    def test_guard_and_reason_default_to_none(self) -> None:
        @check_roles(AdminRole)
        class _Action:
            pass

        assert _Action._role_info["guard"] is None
        assert _Action._role_info["guard_reason"] is None

    def test_guard_without_reason_defaults_to_forbidden_guard(self) -> None:
        def guard_fn(user: object, params: object) -> bool:
            return True

        @check_roles(AdminRole, guard=guard_fn)
        class _Action:
            pass

        assert _Action._role_info["guard_reason"] == FailSecurityVerdict("FORBIDDEN_GUARD")

    def test_reason_without_guard_raises(self) -> None:
        with pytest.raises(ValueError, match=r"reason=.*guard="):

            @check_roles(AdminRole, reason=FailSecurityVerdict("not eligible"))
            class _Action:
                pass

    def test_guard_reason_as_plain_string_raises(self) -> None:
        """baseverdict-audit finding 3, third document -- same gap, same fix, other call site."""

        def guard_fn(user: object, params: object) -> bool:
            return True

        with pytest.raises(TypeError, match="FailSecurityVerdict"):

            @check_roles(AdminRole, guard=guard_fn, reason="not eligible")  # type: ignore[arg-type]
            class _Action:
                pass


class TestAsyncConditionRejected:
    def test_async_when_raises(self) -> None:
        async def when_async(user: object) -> bool:
            return True

        with pytest.raises(AccessConditionAsyncError) as excinfo:

            @check_roles(grant(AdminRole, when=when_async, reason=FailSecurityVerdict("async when")))
            class _Action:
                pass

        assert excinfo.value.condition_name == "when"
        assert excinfo.value.func is when_async

    def test_async_guard_raises(self) -> None:
        async def guard_async(user: object, params: object) -> bool:
            return True

        with pytest.raises(AccessConditionAsyncError) as excinfo:

            @check_roles(AdminRole, guard=guard_async, reason=FailSecurityVerdict("async guard"))
            class _Action:
                pass

        assert excinfo.value.condition_name == "guard"
