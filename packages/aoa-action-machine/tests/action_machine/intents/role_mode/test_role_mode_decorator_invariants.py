# tests/action_machine/intents/role_mode/test_role_mode_decorator_invariants.py
"""
``@role_mode`` accepts one of four members, and refuses anything else where it is written.

Each refusal is exercised the way a developer meets it — a real class statement, evaluated
as a module body would be — so the tests also prove that the class name is never bound and
that the failure happens before any operation is assembled.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import pytest

from aoa.action_machine.exceptions import RoleModeDeclarationError
from aoa.action_machine.intents.role_mode import RoleMode, RoleModeIntent, role_mode

_ALLOWED_IN_ORDER = "ALIVE, DEPRECATED, SILENCED, UNUSED"


class ForeignMode(Enum):
    """Another closed set, carrying the same string values."""

    ALIVE = "alive"


def _namespace() -> dict[str, Any]:
    """Return the globals a declaring module would have for these tests."""
    return {"role_mode": role_mode, "RoleMode": RoleMode, "ForeignMode": ForeignMode}


def _refused(source: str, role_name: str = "ViewerRole") -> RoleModeDeclarationError:
    """Declare a role with ``source`` and return the refusal, asserting the name was never bound."""
    namespace = _namespace()
    with pytest.raises(RoleModeDeclarationError) as caught:
        exec(source, namespace)
    assert role_name not in namespace
    return caught.value


class TestAnArgumentThatIsNotAMember:
    @pytest.mark.parametrize(
        ("source", "received"),
        [
            ('@role_mode("alive")\nclass ViewerRole:\n    pass\n', "'alive'"),
            ("@role_mode(RoleMode.ALIVE.value)\nclass ViewerRole:\n    pass\n", "'alive'"),
            ("@role_mode(42)\nclass ViewerRole:\n    pass\n", "42"),
            ("@role_mode(None)\nclass ViewerRole:\n    pass\n", "None"),
            ("@role_mode(object())\nclass ViewerRole:\n    pass\n", "<object object at "),
            ("@role_mode(ForeignMode.ALIVE)\nclass ViewerRole:\n    pass\n", "ForeignMode.ALIVE"),
            ('@role_mode(mode="alive")\nclass ViewerRole:\n    pass\n', "'alive'"),
        ],
    )
    def test_the_refusal_names_the_role_the_value_and_the_four(self, source: str, received: str) -> None:
        message = str(_refused(source))
        assert "ViewerRole" in message
        assert received in message
        assert _ALLOWED_IN_ORDER in message

    def test_the_refusal_names_the_decorator(self) -> None:
        assert "@role_mode" in str(_refused('@role_mode("alive")\nclass ViewerRole:\n    pass\n'))

    def test_none_and_the_string_none_are_told_apart(self) -> None:
        none_message = str(_refused("@role_mode(None)\nclass ViewerRole:\n    pass\n"))
        string_message = str(_refused('@role_mode("None")\nclass ViewerRole:\n    pass\n'))
        assert "got None." in none_message
        assert "got 'None'." in string_message


class TestTheDecoratorWithoutParentheses:
    def test_the_class_is_named_and_the_parentheses_are_named(self) -> None:
        message = str(_refused("@role_mode\nclass ViewerRole:\n    pass\n"))
        assert "ViewerRole" in message
        assert "the parentheses are missing" in message
        assert _ALLOWED_IN_ORDER in message

    def test_the_failure_is_the_declaration_error_and_not_a_later_issubclass_error(self) -> None:
        error = _refused("@role_mode\nclass ViewerRole:\n    pass\n")
        assert isinstance(error, RoleModeDeclarationError)


class TestTheFourAcceptedMembers:
    @pytest.mark.parametrize("member", list(RoleMode))
    def test_each_member_is_accepted_and_stored_by_identity(self, member: RoleMode) -> None:
        class Plain:
            pass

        decorated = role_mode(member)(Plain)

        assert decorated is Plain
        assert Plain._role_mode_info["mode"] is member


class TestWhatARefusalLeavesBehind:
    def test_a_refused_argument_writes_no_metadata(self) -> None:
        class Plain:
            pass

        with pytest.raises(RoleModeDeclarationError):
            role_mode("alive")(Plain)

        assert not hasattr(Plain, "_role_mode_info")


class TestTheAccessorKeepsItsGuards:
    def test_a_role_without_the_decorator_is_refused(self) -> None:
        class UndecoratedRole(RoleModeIntent):
            pass

        with pytest.raises(RoleModeDeclarationError, match="has no _role_mode_info"):
            RoleMode.declared_for(UndecoratedRole)

    def test_metadata_that_is_not_a_member_is_refused(self) -> None:
        @role_mode(RoleMode.ALIVE)
        class ViewerRole(RoleModeIntent):
            pass

        ViewerRole._role_mode_info = {"mode": "alive"}

        with pytest.raises(RoleModeDeclarationError) as caught:
            RoleMode.declared_for(ViewerRole)

        message = str(caught.value)
        assert "invalid _role_mode_info['mode']" in message
        assert "DEPRECATED" not in message
