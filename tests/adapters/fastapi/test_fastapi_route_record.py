# tests/adapters/fastapi/test_fastapi_route_record.py
"""
Tests for FastApiRouteRecord — frozen dataclass with HTTP-specific fields.

FastApiRouteRecord extends BaseRouteRecord with method, path, tags, summary,
description, operation_id, deprecated. It validates that method is from the
allowed set {GET, POST, PUT, DELETE, PATCH}, normalizes it to uppercase,
and checks that path is non-empty and starts with '/'.

Scenarios covered:
    - Default field values (method="POST", path="/", tags=(), etc.).
    - Method normalization: lowercase → uppercase.
    - All five allowed methods accepted.
    - Invalid method raises ValueError.
    - Empty path raises ValueError.
    - Path not starting with '/' raises ValueError.
    - Whitespace-only path raises ValueError.
    - Tags stored as tuple.
    - Optional fields (summary, description, operation_id, deprecated) stored correctly.
    - Frozen immutability — fields cannot be modified after creation.
    - Inherited BaseRouteRecord invariants still enforced (action_class, mappers).
"""

import pytest

from action_machine.contrib.fastapi.route_record import FastApiRouteRecord
from tests.domain import PingAction, SimpleAction

# ═════════════════════════════════════════════════════════════════════════════
# Default field values
# ═════════════════════════════════════════════════════════════════════════════


class TestDefaults:
    """Verify default values of HTTP-specific fields."""

    def test_default_method(self) -> None:
        """Default method is 'POST'."""
        record = FastApiRouteRecord(action_class=PingAction, path="/ping")
        assert record.method == "POST"

    def test_default_path(self) -> None:
        """Default path is '/'."""
        record = FastApiRouteRecord(action_class=PingAction)
        assert record.path == "/"

    def test_default_tags(self) -> None:
        """Default tags is an empty tuple."""
        record = FastApiRouteRecord(action_class=PingAction)
        assert record.tags == ()

    def test_default_summary(self) -> None:
        """Default summary is an empty string."""
        record = FastApiRouteRecord(action_class=PingAction)
        assert record.summary == ""

    def test_default_description(self) -> None:
        """Default description is an empty string."""
        record = FastApiRouteRecord(action_class=PingAction)
        assert record.description == ""

    def test_default_operation_id(self) -> None:
        """Default operation_id is None."""
        record = FastApiRouteRecord(action_class=PingAction)
        assert record.operation_id is None

    def test_default_deprecated(self) -> None:
        """Default deprecated is False."""
        record = FastApiRouteRecord(action_class=PingAction)
        assert record.deprecated is False


# ═════════════════════════════════════════════════════════════════════════════
# Method validation and normalization
# ═════════════════════════════════════════════════════════════════════════════


class TestMethodValidation:
    """Verify method normalization to uppercase and allowed set enforcement."""

    def test_lowercase_normalized(self) -> None:
        """A lowercase method string is normalized to uppercase."""
        record = FastApiRouteRecord(action_class=PingAction, method="get", path="/ping")
        assert record.method == "GET"

    def test_mixed_case_normalized(self) -> None:
        """A mixed-case method string is normalized to uppercase."""
        record = FastApiRouteRecord(action_class=PingAction, method="Post", path="/ping")
        assert record.method == "POST"

    @pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE", "PATCH"])
    def test_all_allowed_methods(self, method: str) -> None:
        """All five standard HTTP methods are accepted."""
        record = FastApiRouteRecord(action_class=PingAction, method=method, path="/test")
        assert record.method == method

    def test_invalid_method_raises(self) -> None:
        """An unsupported HTTP method raises ValueError."""
        with pytest.raises(ValueError, match="method"):
            FastApiRouteRecord(action_class=PingAction, method="OPTIONS", path="/test")

    def test_empty_method_raises(self) -> None:
        """An empty method string raises ValueError."""
        with pytest.raises(ValueError):
            FastApiRouteRecord(action_class=PingAction, method="", path="/test")


# ═════════════════════════════════════════════════════════════════════════════
# Path validation
# ═════════════════════════════════════════════════════════════════════════════


class TestPathValidation:
    """Verify path must be non-empty and start with '/'."""

    def test_valid_path(self) -> None:
        """A path starting with '/' is accepted."""
        record = FastApiRouteRecord(action_class=PingAction, path="/api/v1/ping")
        assert record.path == "/api/v1/ping"

    def test_path_with_params(self) -> None:
        """A path with FastAPI-style parameters is accepted."""
        record = FastApiRouteRecord(action_class=PingAction, path="/orders/{order_id}")
        assert record.path == "/orders/{order_id}"

    def test_missing_leading_slash_raises(self) -> None:
        """A path not starting with '/' raises ValueError."""
        with pytest.raises(ValueError, match="path"):
            FastApiRouteRecord(action_class=PingAction, path="api/ping")

    def test_empty_path_raises(self) -> None:
        """An empty path raises ValueError."""
        with pytest.raises(ValueError, match="path"):
            FastApiRouteRecord(action_class=PingAction, path="")

    def test_whitespace_only_path_raises(self) -> None:
        """A whitespace-only path raises ValueError."""
        with pytest.raises(ValueError, match="path"):
            FastApiRouteRecord(action_class=PingAction, path="   ")


# ═════════════════════════════════════════════════════════════════════════════
# Optional fields
# ═════════════════════════════════════════════════════════════════════════════


class TestOptionalFields:
    """Verify that optional HTTP-specific fields are stored correctly."""

    def test_tags_stored_as_tuple(self) -> None:
        """Tags passed as a tuple are stored unchanged."""
        record = FastApiRouteRecord(
            action_class=PingAction,
            path="/ping",
            tags=("system", "health"),
        )
        assert record.tags == ("system", "health")

    def test_summary_stored(self) -> None:
        """A custom summary is stored and retrievable."""
        record = FastApiRouteRecord(
            action_class=PingAction,
            path="/ping",
            summary="Check service health",
        )
        assert record.summary == "Check service health"

    def test_description_stored(self) -> None:
        """A custom description is stored and retrievable."""
        record = FastApiRouteRecord(
            action_class=PingAction,
            path="/ping",
            description="Returns pong if the service is alive.",
        )
        assert record.description == "Returns pong if the service is alive."

    def test_operation_id_stored(self) -> None:
        """A custom operation_id is stored and retrievable."""
        record = FastApiRouteRecord(
            action_class=PingAction,
            path="/ping",
            operation_id="ping_service",
        )
        assert record.operation_id == "ping_service"

    def test_deprecated_flag(self) -> None:
        """The deprecated flag is stored and retrievable."""
        record = FastApiRouteRecord(
            action_class=PingAction,
            path="/ping",
            deprecated=True,
        )
        assert record.deprecated is True


# ═════════════════════════════════════════════════════════════════════════════
# Frozen immutability
# ═════════════════════════════════════════════════════════════════════════════


class TestFrozen:
    """Verify that FastApiRouteRecord is truly frozen."""

    def test_cannot_modify_method(self) -> None:
        """Attempting to change method raises AttributeError."""
        record = FastApiRouteRecord(action_class=PingAction, path="/ping")

        with pytest.raises(AttributeError):
            record.method = "GET"  # type: ignore[misc]

    def test_cannot_modify_path(self) -> None:
        """Attempting to change path raises AttributeError."""
        record = FastApiRouteRecord(action_class=PingAction, path="/ping")

        with pytest.raises(AttributeError):
            record.path = "/other"  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════════
# Inherited BaseRouteRecord invariants
# ═════════════════════════════════════════════════════════════════════════════


class TestInheritedInvariants:
    """Verify BaseRouteRecord validations still apply to FastApiRouteRecord."""

    def test_non_action_raises(self) -> None:
        """A non-BaseAction class triggers TypeError from BaseRouteRecord."""

        class _Plain:
            pass

        with pytest.raises(TypeError, match="BaseAction"):
            FastApiRouteRecord(action_class=_Plain, path="/test")

    def test_type_extraction_works(self) -> None:
        """params_type and result_type are extracted from the action class."""
        record = FastApiRouteRecord(action_class=SimpleAction, path="/simple")
        assert record.params_type is SimpleAction.Params
        assert record.result_type is SimpleAction.Result
