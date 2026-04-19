# tests/intents/context/test_user_info.py
"""
Tests for UserInfo — user identity in the execution context.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

UserInfo is a frozen pydantic model (subclass of BaseSchema) holding user id
and role types. It is part of Context and used by the machine for role checks
via ActionProductMachine._check_action_roles().

UserInfo is created by:
- AuthCoordinator.process() — authenticated real requests.
- NoAuthCoordinator.process() — anonymous user (user_id=None, roles=()).
- Directly in tests — UserInfo(...).

Arbitrary fields are forbidden (extra="forbid"). Extend only via subclasses
with explicitly declared fields.

═══════════════════════════════════════════════════════════════════════════════
COVERED SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

Construction:
    - Full field set (user_id, roles).
    - Minimal data (user_id only).
    - No arguments — user_id=None, roles=().
    - user_id=None — anonymous user.

BaseSchema — dict-like access:
    - __getitem__, __contains__, get, keys, values, items.
    - KeyError for unknown fields.

BaseSchema — resolve:
    - Flat fields: resolve("user_id"), resolve("roles").
    - Missing paths: resolve("missing") → None.

Extension via inheritance:
    - Subclass with extra fields (org, settings).
    - resolve on subclass: resolve("org"), resolve("settings.theme").
"""

from typing import Any

import pytest
from pydantic import ConfigDict

from action_machine.context.user_info import UserInfo
from tests.scenarios.domain_model.roles import AdminRole, GuestRole, ManagerRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
# UserInfo subclass for extension tests
# ═════════════════════════════════════════════════════════════════════════════


class _ExtendedUserInfo(UserInfo):
    """UserInfo subclass with extra fields for tests."""
    model_config = ConfigDict(frozen=True)
    org: str | None = None
    department: str | None = None
    settings: dict[str, Any] = {}


# ═════════════════════════════════════════════════════════════════════════════
# Construction and initialization
# ═════════════════════════════════════════════════════════════════════════════


class TestUserInfoCreation:
    """Creating UserInfo with different argument sets."""

    def test_create_with_all_fields(self) -> None:
        """
        UserInfo with all fields — typical authenticated user.

        AuthCoordinator.process() builds UserInfo from token or API key data:
        user_id and roles.
        """
        # Arrange & Act — full field set
        user = UserInfo(
            user_id="agent_007",
            roles=(AdminRole, ManagerRole),
        )

        # Assert — all fields set
        assert user.user_id == "agent_007"
        assert user.roles == (AdminRole, ManagerRole)

    def test_create_with_user_id_only(self) -> None:
        """
        UserInfo with user_id only — minimal authenticated user.
        roles defaults to ().
        """
        # Arrange & Act — user_id only
        user = UserInfo(user_id="u42")

        # Assert — user_id set, default roles
        assert user.user_id == "u42"
        assert user.roles == ()

    def test_create_default(self) -> None:
        """
        UserInfo with no arguments — anonymous user.
        NoAuthCoordinator builds Context with UserInfo() — defaults
        user_id=None, roles=().
        """
        # Arrange & Act — no arguments
        user = UserInfo()

        # Assert — default fields
        assert user.user_id is None
        assert user.roles == ()

    def test_create_with_none_user_id(self) -> None:
        """
        user_id=None — explicitly anonymous.
        Same defaults as UserInfo(), but can be set explicitly when
        building context for guest access.
        """
        # Arrange & Act — explicit None
        user = UserInfo(user_id=None, roles=(GuestRole,))

        # Assert — user_id=None but role set
        assert user.user_id is None
        assert user.roles == (GuestRole,)

    def test_roles_none_coerces_to_empty_tuple(self) -> None:
        user = UserInfo(user_id="u1", roles=None)
        assert user.roles == ()

    def test_roles_non_sequence_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="list or tuple"):
            UserInfo(roles=object())  # type: ignore[arg-type, call-overload]

    def test_roles_item_not_role_subclass_raises(self) -> None:
        with pytest.raises(TypeError, match=r"UserInfo\.roles\[0\]"):
            UserInfo(roles=(42,))  # type: ignore[arg-type, call-overload]

    def test_extended_user_info_with_extra_fields(self) -> None:
        """
        Extend UserInfo via subclass with explicit fields.

        UserInfo uses extra="forbid" — arbitrary fields are not allowed.
        Use a subclass for extra data.
        """
        # Arrange & Act — subclass with extra fields
        user = _ExtendedUserInfo(
            user_id="agent_007",
            roles=(AdminRole, ManagerRole),
            org="acme",
            department="sales",
        )

        # Assert — all fields set
        assert user.user_id == "agent_007"
        assert user.roles == (AdminRole, ManagerRole)
        assert user.org == "acme"
        assert user.department == "sales"


# ═════════════════════════════════════════════════════════════════════════════
# BaseSchema — dict-like access
# ═════════════════════════════════════════════════════════════════════════════


class TestUserInfoDictAccess:
    """Dict-like access to UserInfo fields via BaseSchema."""

    def test_getitem(self) -> None:
        """
        user["user_id"] — bracket access to a field.
        BaseSchema.__getitem__ delegates to getattr(self, key).
        """
        # Arrange — UserInfo with user_id
        user = UserInfo(user_id="agent_007")

        # Act & Assert — bracket read
        assert user["user_id"] == "agent_007"

    def test_getitem_missing_raises_key_error(self) -> None:
        """
        user["nonexistent"] → KeyError.
        BaseSchema.__getitem__ catches AttributeError and re-raises
        as KeyError — same as dict.
        """
        # Arrange — UserInfo without "nonexistent"
        user = UserInfo(user_id="u1")

        # Act & Assert — KeyError for unknown key
        with pytest.raises(KeyError):
            _ = user["nonexistent"]

    def test_contains(self) -> None:
        """
        "user_id" in user → True; "missing" in user → False.
        BaseSchema.__contains__ checks model_fields.
        """
        # Arrange
        user = UserInfo(user_id="u1", roles=(AdminRole,))

        # Act & Assert — declared fields
        assert "user_id" in user
        assert "roles" in user
        assert "nonexistent" not in user

    def test_get_existing(self) -> None:
        """
        user.get("user_id") → field value.
        """
        # Arrange
        user = UserInfo(user_id="u1")

        # Act & Assert
        assert user.get("user_id") == "u1"

    def test_get_missing_with_default(self) -> None:
        """
        user.get("missing", "fallback") → "fallback".
        """
        # Arrange
        user = UserInfo(user_id="u1")

        # Act & Assert — missing key with default
        assert user.get("nonexistent", "fallback") == "fallback"

    def test_get_missing_without_default(self) -> None:
        """
        user.get("missing") → None (default when omitted).
        """
        # Arrange
        user = UserInfo(user_id="u1")

        # Act & Assert
        assert user.get("nonexistent") is None

    def test_keys(self) -> None:
        """
        keys() returns declared pydantic fields.
        UserInfo has two fields: user_id, roles.
        """
        # Arrange
        user = UserInfo(user_id="u1", roles=(AdminRole,))

        # Act
        keys = user.keys()

        # Assert — two declared fields
        assert "user_id" in keys
        assert "roles" in keys

    def test_values(self) -> None:
        """
        values() returns values of declared fields.
        """
        # Arrange
        user = UserInfo(user_id="u1", roles=(AdminRole,))

        # Act
        values = user.values()

        # Assert — values present
        assert "u1" in values
        assert (AdminRole,) in values

    def test_items(self) -> None:
        """
        items() returns (key, value) pairs for declared fields.
        """
        # Arrange
        user = UserInfo(user_id="u1")

        # Act
        items = user.items()

        # Assert — ("user_id", "u1") present
        assert ("user_id", "u1") in items


# ═════════════════════════════════════════════════════════════════════════════
# BaseSchema — resolve
# ═════════════════════════════════════════════════════════════════════════════


class TestUserInfoResolve:
    """Field navigation on UserInfo via resolve()."""

    def test_resolve_flat_field(self) -> None:
        """
        resolve("user_id") — direct access to a flat field.
        """
        # Arrange
        user = UserInfo(user_id="agent_007")

        # Act
        result = user.resolve("user_id")

        # Assert
        assert result == "agent_007"

    def test_resolve_roles(self) -> None:
        """
        resolve("roles") — access to the role types tuple.
        """
        # Arrange
        user = UserInfo(roles=(AdminRole, UserRole))

        # Act
        result = user.resolve("roles")

        # Assert — full tuple
        assert result == (AdminRole, UserRole)

    def test_resolve_extended_field(self) -> None:
        """
        resolve("org") on subclass — navigate to subclass field.
        """
        # Arrange — subclass with org
        user = _ExtendedUserInfo(org="acme")

        # Act
        result = user.resolve("org")

        # Assert
        assert result == "acme"

    def test_resolve_extended_nested_dict(self) -> None:
        """
        resolve("settings.theme") on subclass — navigation through a dict field.

        Two steps: _ExtendedUserInfo → settings (dict) → theme (str).
        resolve switches from BaseSchema.__getitem__ to dict access.
        """
        # Arrange — subclass with settings dict
        user = _ExtendedUserInfo(settings={"theme": "dark", "lang": "ru"})

        # Act
        result = user.resolve("settings.theme")

        # Assert
        assert result == "dark"

    def test_resolve_missing_returns_none(self) -> None:
        """
        resolve("nonexistent") — missing field → None.
        resolve does not raise when a key is missing.
        """
        # Arrange
        user = UserInfo(user_id="u1")

        # Act
        result = user.resolve("nonexistent")

        # Assert — None as default
        assert result is None

    def test_resolve_missing_with_default(self) -> None:
        """
        resolve("nonexistent", default="N/A") → "N/A".
        """
        # Arrange
        user = UserInfo(user_id="u1")

        # Act
        result = user.resolve("nonexistent", default="N/A")

        # Assert
        assert result == "N/A"

    def test_resolve_none_user_id(self) -> None:
        """
        resolve("user_id") when user_id=None → returns None, not default.
        None is a valid field value, not “missing”.
        """
        # Arrange — explicit None user_id
        user = UserInfo(user_id=None)

        # Act
        result = user.resolve("user_id", default="fallback")

        # Assert — None from field, not "fallback"
        assert result is None


class TestUserInfoSerialization:
    """JSON projection of UserInfo serializes roles as string role names."""

    def test_model_dump_json_mode_serializes_roles_as_names(self) -> None:
        user = UserInfo(user_id="u1", roles=(AdminRole, UserRole))

        dumped = user.model_dump(mode="json")

        assert dumped["user_id"] == "u1"
        assert dumped["roles"] == [AdminRole.name, UserRole.name]

    def test_model_dump_json_string_serializes_roles_as_names(self) -> None:
        user = UserInfo(user_id="u1", roles=(ManagerRole,))

        dumped_json = user.model_dump_json()

        assert '"roles":["manager"]' in dumped_json
