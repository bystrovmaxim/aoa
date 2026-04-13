# tests/auth/test_check_roles_class_roles.py
"""
Golden tests for ``BaseRole``, ``@role_mode``, and ``@check_roles``.

Covers import-time validation, decorator guards, and normalization of typed
role specs for the coordinator snapshot.
"""

from __future__ import annotations

import pytest

from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.auth.base_role import BaseRole
from action_machine.intents.auth.check_roles_decorator import check_roles
from action_machine.intents.auth.role_intent import RoleIntent
from action_machine.intents.auth.role_mode_decorator import RoleMode, role_mode
from action_machine.intents.context.user_info import UserInfo
from action_machine.intents.meta.meta_decorator import meta
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.model.exceptions import NamingSuffixError
from tests.scenarios.domain_model.domains import TestDomain


class TestRoleModeDecorator:
    def test_role_mode_requires_role_mode_intent(self) -> None:
        class Plain:
            pass

        with pytest.raises(TypeError, match="RoleModeIntent"):
            role_mode(RoleMode.ALIVE)(Plain)  # type: ignore[arg-type]


class TestBaseRoleValidation:
    def test_suffix_required(self) -> None:
        with pytest.raises(NamingSuffixError):

            class Bad(BaseRole):  # type: ignore[misc]
                name = "x"
                description = "y"


@role_mode(RoleMode.ALIVE)
class _ViewerRole(BaseRole):
    name = "viewer"
    description = "View access."


@role_mode(RoleMode.ALIVE)
class _EditorRole(_ViewerRole):
    name = "hand_editor"
    description = "Edit access."


class TestUserInfoRoles:
    def test_roles_must_be_base_role_types(self) -> None:
        with pytest.raises(TypeError, match=r"UserInfo\.roles\[0\]"):
            UserInfo(user_id="u1", roles=["admin"])  # type: ignore[arg-type]

    def test_roles_accepts_list_of_role_classes(self) -> None:
        u = UserInfo(user_id="u1", roles=[_ViewerRole])
        assert u.roles == (_ViewerRole,)


class TestCheckRolesNormalization:
    def test_string_spec_raises(self) -> None:
        with pytest.raises(TypeError, match="does not accept role name strings"):
            check_roles("admin")

    def test_list_of_strings_raises(self) -> None:
        with pytest.raises(TypeError, match="does not accept list\\[str\\]"):
            check_roles(["manager", "editor"])

    def test_single_role_type_stored(self) -> None:
        class _P(BaseParams):
            pass

        class _R(BaseResult):
            pass

        @meta(description="norm type", domain=TestDomain)
        @check_roles(_EditorRole)
        class _NormTypeAction(BaseAction[_P, _R]):
            @summary_aspect("s")
            async def build_summary(self, params, state, box, connections):
                return _R()

        assert _NormTypeAction._role_info["spec"] is _EditorRole
        assert issubclass(_NormTypeAction, RoleIntent)

    def test_list_of_role_types_becomes_tuple(self) -> None:
        class _P(BaseParams):
            pass

        class _R(BaseResult):
            pass

        @meta(description="multi role", domain=TestDomain)
        @check_roles([_EditorRole, _ViewerRole])
        class _MultiRolesAction(BaseAction[_P, _R]):
            @summary_aspect("s")
            async def build_summary(self, params, state, box, connections):
                return _R()

        spec = _MultiRolesAction._role_info["spec"]
        assert isinstance(spec, tuple)
        assert len(spec) == 2
        assert spec[0] is _EditorRole
        assert spec[1] is _ViewerRole

    def test_mixed_list_raises(self) -> None:
        with pytest.raises(TypeError, match="list\\[str\\]"):
            check_roles(["admin", _ViewerRole])  # type: ignore[list-item]

    def test_non_base_role_type_raises(self) -> None:
        class NotRole:
            pass

        with pytest.raises(TypeError, match="BaseRole"):
            check_roles(NotRole)  # type: ignore[arg-type]
