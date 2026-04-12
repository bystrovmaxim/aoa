# tests/auth/test_check_roles_class_roles.py
"""
PR-1 golden tests: ``BaseRole``, ``@role_mode``, ``StringRoleRegistry``, ``@check_roles``.

Covers import-time validation, decorator guards, and normalization of typed
role specs for the coordinator snapshot.
"""

from __future__ import annotations

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.base_role import BaseRole
from action_machine.auth.check_roles import check_roles
from action_machine.auth.role_gate_host import RoleGateHost
from action_machine.auth.role_mode import RoleMode
from action_machine.auth.role_mode_decorator import role_mode
from action_machine.auth.string_role_registry import StringRoleRegistry
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.exceptions import NamingSuffixError
from action_machine.core.meta_decorator import meta
from tests.domain_model.domains import TestDomain


class TestRoleModeDecorator:
    def test_role_mode_requires_role_mode_gate_host(self) -> None:
        class Plain:
            pass

        with pytest.raises(TypeError, match="RoleModeGateHost"):
            role_mode(RoleMode.ALIVE)(Plain)  # type: ignore[arg-type]


class TestBaseRoleValidation:
    def test_suffix_required(self) -> None:
        with pytest.raises(NamingSuffixError):

            class Bad(BaseRole):  # type: ignore[misc]
                name = "x"
                description = "y"
                includes = ()

    def test_includes_must_be_role_types(self) -> None:
        with pytest.raises(TypeError, match="includes"):

            @role_mode(RoleMode.ALIVE)
            class BadIncludesRole(BaseRole):
                name = "bad"
                description = "bad"
                includes = (object,)  # type: ignore[assignment]


@role_mode(RoleMode.ALIVE)
class _ViewerRole(BaseRole):
    name = "viewer"
    description = "View access."
    includes = ()


@role_mode(RoleMode.ALIVE)
class _EditorRole(BaseRole):
    name = "hand_editor"
    description = "Edit access."
    includes = (_ViewerRole,)


class TestStringRoleRegistry:
    def test_resolve_is_cached_and_lowercase(self) -> None:
        # Key must not collide with declared domain roles (admin/manager/editor).
        a1 = StringRoleRegistry.resolve("SynthProbe")
        a2 = StringRoleRegistry.resolve("synthprobe")
        assert a1 is a2
        assert a1.name == "synthprobe"
        assert issubclass(a1, BaseRole)
        assert a1._role_mode_info["mode"] is RoleMode.ALIVE


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
        assert issubclass(_NormTypeAction, RoleGateHost)

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
