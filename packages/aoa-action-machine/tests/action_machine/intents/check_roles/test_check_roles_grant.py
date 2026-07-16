"""Golden tests for grant(...)/guard= on @check_roles (access-control-cascade step 4)."""

from __future__ import annotations

import pytest

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.exceptions import AccessConditionAsyncError
from aoa.action_machine.intents.check_roles.check_roles_decorator import check_roles
from aoa.action_machine.intents.check_roles.grant import Grant, grant

from ....support.domain_model.roles import AdminRole, ManagerRole


def _sales_only(user: object) -> bool:
    return True


class TestGrantConstruction:
    def test_grant_stores_role_and_when(self) -> None:
        g = grant(AdminRole, when=_sales_only)
        assert g.role is AdminRole
        assert g.when is _sales_only

    def test_grant_when_defaults_to_none(self) -> None:
        g = grant(AdminRole)
        assert g.when is None

    def test_grant_rejects_non_role(self) -> None:
        class NotRole:
            pass

        with pytest.raises(TypeError, match="BaseRole"):
            grant(NotRole)  # type: ignore[arg-type]


class TestCheckRolesGrants:
    def test_single_grant_spec_is_bare_type(self) -> None:
        @check_roles(grant(AdminRole))
        class _Action:
            pass

        assert _Action._role_info["spec"] is AdminRole
        assert _Action._role_info["grants"] == [Grant(role=AdminRole, when=None)]
        assert _Action._role_info["guard"] is None

    def test_multiple_grants_preserved_in_order(self) -> None:
        @check_roles(grant(AdminRole), grant(ManagerRole, when=_sales_only))
        class _Action:
            pass

        grants = _Action._role_info["grants"]
        assert len(grants) == 2
        assert grants[0] == Grant(role=AdminRole, when=None)
        assert grants[1].role is ManagerRole
        assert grants[1].when is _sales_only
        assert _Action._role_info["spec"] == (AdminRole, ManagerRole)

    def test_bare_role_and_grant_mixed(self) -> None:
        @check_roles(AdminRole, grant(ManagerRole, when=_sales_only))
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
    def test_guard_stored(self) -> None:
        def guard_fn(user: object, params: object) -> bool:
            return True

        @check_roles(AdminRole, guard=guard_fn)
        class _Action:
            pass

        assert _Action._role_info["guard"] is guard_fn

    def test_guard_defaults_to_none(self) -> None:
        @check_roles(AdminRole)
        class _Action:
            pass

        assert _Action._role_info["guard"] is None


class TestAsyncConditionRejected:
    def test_async_when_raises(self) -> None:
        async def when_async(user: object) -> bool:
            return True

        with pytest.raises(AccessConditionAsyncError) as excinfo:

            @check_roles(grant(AdminRole, when=when_async))
            class _Action:
                pass

        assert excinfo.value.condition_name == "when"
        assert excinfo.value.func is when_async

    def test_async_guard_raises(self) -> None:
        async def guard_async(user: object, params: object) -> bool:
            return True

        with pytest.raises(AccessConditionAsyncError) as excinfo:

            @check_roles(AdminRole, guard=guard_async)
            class _Action:
                pass

        assert excinfo.value.condition_name == "guard"
