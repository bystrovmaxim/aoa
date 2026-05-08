# tests/model/test_resolve_missing.py
"""
Tests for BaseSchema.resolve() on missing keys and paths.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

resolve() never raises on missing keys. It returns default (None by default).
Logging templates ({%state.missing_field}) must not break the pipeline.

At each step resolve checks the current object type:
- BaseSchema → __getitem__, KeyError → return default.
- dict → key check, missing → return default.
- other object → getattr, missing → return default.

═══════════════════════════════════════════════════════════════════════════════
COVERED SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

Missing flat field:
    - resolve("missing") → None (default).
    - resolve("missing", default="X") → "X".
    - No KeyError or AttributeError.

Missing nested field:
    - resolve("user.nonexistent.deep") → default.
    - resolve("settings.missing.nested") → default (via subclass).

Missing intermediate key:
    - resolve("user.missing.key.deep") → default.
    - resolve("settings.existing.missing.deep") → default.
    - resolve("missing.segment.deep") → default (first segment).

Various default types:
    - str, int, list, dict, bool, None.

None as value vs missing:
    - Field exists and is None → None, not default.
    - Field missing → default.
    - Dict key exists with None → None, not default.
    - Dict key missing → default.
"""

from typing import Any

from pydantic import ConfigDict

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.request_info import RequestInfo
from aoa.action_machine.context.runtime_info import RuntimeInfo
from aoa.action_machine.context.user_info import UserInfo
from tests.action_machine.scenarios.domain_model.roles import AdminRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
# Info subclasses for nested navigation tests
# ═════════════════════════════════════════════════════════════════════════════


class _ExtendedUserInfo(UserInfo):
    """UserInfo subclass with extra fields for tests."""
    model_config = ConfigDict(frozen=True)
    org: str | None = None
    settings: dict[str, Any] = {}


# ═════════════════════════════════════════════════════════════════════════════
# Helper
# ═════════════════════════════════════════════════════════════════════════════


def _make_full_context(user_id: str = "agent_1") -> Context:
    """
    Context with all components for nested path tests.

    Uses _ExtendedUserInfo with org for three-level navigation.
    """
    user = _ExtendedUserInfo(
        user_id=user_id,
        roles=(UserRole, AdminRole),
        org="acme",
    )
    request = RequestInfo(
        trace_id="trace-abc-123",
        request_path="/api/v1/orders",
        request_method="POST",
    )
    runtime = RuntimeInfo(
        hostname="pod-xyz-42",
        service_name="order-service",
    )
    return Context(user=user, request=request, runtime=runtime)


# ═════════════════════════════════════════════════════════════════════════════
# Missing flat field
# ═════════════════════════════════════════════════════════════════════════════


class TestMissingFlat:
    """Missing flat field — resolve returns default."""

    def test_missing_returns_none_by_default(self) -> None:
        """
        resolve("nonexistent") without default returns None.
        """
        # Arrange
        user = UserInfo(user_id="42")

        # Act
        result = user.resolve("nonexistent")

        # Assert
        assert result is None

    def test_missing_returns_explicit_default(self) -> None:
        """
        resolve("missing", default="<none>") returns that default.
        """
        # Arrange
        user = UserInfo(user_id="42")

        # Act
        result = user.resolve("missing", default="<none>")

        # Assert
        assert result == "<none>"

    def test_missing_does_not_raise(self) -> None:
        """
        resolve never raises KeyError or AttributeError.
        Critical for logging templates.
        """
        # Arrange
        user = UserInfo(user_id="42")

        # Act
        result_flat = user.resolve("missing")
        result_nested = user.resolve("missing.key")

        # Assert
        assert result_flat is None
        assert result_nested is None


# ═════════════════════════════════════════════════════════════════════════════
# Missing nested field
# ═════════════════════════════════════════════════════════════════════════════


class TestMissingNested:
    """Missing field at nested level — resolve returns default."""

    def test_missing_in_schema(self) -> None:
        """
        resolve("user.nonexistent.deep") — "nonexistent" missing on UserInfo.

        Step 1: Context → UserInfo (OK).
        Step 2: UserInfo → "nonexistent" → KeyError → default.
        """
        # Arrange
        ctx = _make_full_context()

        # Act
        result = ctx.resolve("user.nonexistent.deep", default="N/A")

        # Assert
        assert result == "N/A"

    def test_missing_in_dict(self) -> None:
        """
        resolve("user.settings.missing.deep") — "missing" not in settings dict.

        Step 1: Context → _ExtendedUserInfo (OK).
        Step 2: settings dict (OK).
        Step 3: dict → "missing" → not found → default.
        """
        # Arrange
        user = _ExtendedUserInfo(settings={"existing": "value"})

        # Act
        result = user.resolve("settings.missing.deep", default="not found")

        # Assert
        assert result == "not found"

    def test_missing_with_default_none(self) -> None:
        """
        resolve("user.nonexistent.deep", default=None) — explicit None default.
        """
        # Arrange
        ctx = _make_full_context()

        # Act
        result = ctx.resolve("user.nonexistent.deep", default=None)

        # Assert
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Missing intermediate key in chain
# ═════════════════════════════════════════════════════════════════════════════


class TestMissingIntermediate:
    """Missing intermediate key in a long path."""

    def test_missing_intermediate_in_schema(self) -> None:
        """
        resolve("user.missing.key.deep") — "missing" not on UserInfo.
        Chain stops at second segment.
        """
        # Arrange
        ctx = _make_full_context()

        # Act
        result = ctx.resolve("user.missing.key.deep", default="fallback")

        # Assert
        assert result == "fallback"

    def test_missing_intermediate_in_dict(self) -> None:
        """
        resolve("settings.existing.missing.deep") — "existing" found,
        "missing" not under it.
        """
        # Arrange
        user = _ExtendedUserInfo(settings={"existing": {"key": "value"}})

        # Act
        result = user.resolve("settings.existing.missing.deep", default="none")

        # Assert
        assert result == "none"

    def test_missing_first_segment(self) -> None:
        """
        resolve("missing.segment.deep") — first segment missing.
        """
        # Arrange
        user = UserInfo(user_id="42")

        # Act
        result = user.resolve("missing.segment.deep", default="first missing")

        # Assert
        assert result == "first missing"


# ═════════════════════════════════════════════════════════════════════════════
# Various default types
# ═════════════════════════════════════════════════════════════════════════════


class TestDefaultTypes:
    """resolve returns default of any type when path missing."""

    def test_default_string(self) -> None:
        """default is str."""
        user = UserInfo(user_id="42")
        result = user.resolve("missing", default="default string")
        assert result == "default string"

    def test_default_int(self) -> None:
        """default is int."""
        user = UserInfo(user_id="42")
        result = user.resolve("missing", default=42)
        assert result == 42

    def test_default_list(self) -> None:
        """default is list."""
        user = UserInfo(user_id="42")
        result = user.resolve("missing", default=[1, 2, 3])
        assert result == [1, 2, 3]

    def test_default_dict(self) -> None:
        """default is dict."""
        user = UserInfo(user_id="42")
        result = user.resolve("missing", default={"key": "value"})
        assert result == {"key": "value"}

    def test_default_bool_true(self) -> None:
        """default is True."""
        user = UserInfo(user_id="42")
        result = user.resolve("missing_true", default=True)
        assert result is True

    def test_default_bool_false(self) -> None:
        """default is False."""
        user = UserInfo(user_id="42")
        result = user.resolve("missing_false", default=False)
        assert result is False


# ═════════════════════════════════════════════════════════════════════════════
# None as value vs missing field
# ═════════════════════════════════════════════════════════════════════════════


class TestNoneVsMissing:
    """
    “Field exists with None” vs “field missing”.
    """

    def test_existing_none_field_returns_none(self) -> None:
        """
        user_id=None — field exists.
        resolve returns None, not default.
        """
        # Arrange
        user = UserInfo(user_id=None)

        # Act
        result = user.resolve("user_id", default="fallback")

        # Assert
        assert result is None

    def test_missing_field_returns_default(self) -> None:
        """
        "nonexistent" missing → default.
        """
        # Arrange
        user = UserInfo(user_id="42")

        # Act
        result = user.resolve("nonexistent", default="fallback")

        # Assert
        assert result == "fallback"

    def test_none_in_dict_returns_none(self) -> None:
        """
        Dict key exists with None — resolve returns None.
        """
        # Arrange
        user = _ExtendedUserInfo(settings={"key_with_none": None})

        # Act
        result = user.resolve("settings.key_with_none", default="fallback")

        # Assert
        assert result is None

    def test_missing_key_in_dict_returns_default(self) -> None:
        """
        Dict key missing — default.
        """
        # Arrange
        user = _ExtendedUserInfo(settings={"existing": "value"})

        # Act
        result = user.resolve("settings.missing_key", default="fallback")

        # Assert
        assert result == "fallback"
