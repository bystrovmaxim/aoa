# tests/adapters/mcp/test_mcp_route_record.py
"""
Tests for ``McpRouteRecord`` — MCP tool metadata on ``BaseRouteRecord``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Validate ``tool_name`` (non-empty after strip, dotted names allowed),
``description``, defaults, immutability, inherited type extraction, and mapper
invariants with local ``_AltRequest`` / ``_AltResponse`` helpers.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    Scenario action class
              |
              v
    McpRouteRecord(tool_name, description, action_class, ...)
              |
              v
    Construction-time validation only (no MCP wire protocol)

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- ``tool_name`` must contain at least one non-space character after stripping.
- ``BaseRouteRecord`` rules for ``action_class`` and mappers still apply.

"""

import pytest
from pydantic import BaseModel

from aoa.action_machine.integrations.mcp.route_record import McpRouteRecord
from tests.action_machine.scenarios.domain_model import FullAction, PingAction, SimpleAction

# ─────────────────────────────────────────────────────────────────────────────
# Helper models for mapper invariant tests — intentionally simple,
# not part of the shared domain.
# ─────────────────────────────────────────────────────────────────────────────


class _AltRequest(BaseModel):
    """Alternative request model for mapper tests."""
    query: str = "test"


class _AltResponse(BaseModel):
    """Alternative response model for mapper tests."""
    data: str = "ok"


# ═════════════════════════════════════════════════════════════════════════════
# tool_name validation
# ═════════════════════════════════════════════════════════════════════════════


class TestToolNameValidation:
    """Verify tool_name must be non-empty after strip."""

    def test_valid_tool_name(self) -> None:
        """A non-empty tool_name is accepted and stored."""
        record = McpRouteRecord(action_class=PingAction, tool_name="system.ping")
        assert record.tool_name == "system.ping"

    def test_empty_tool_name_raises(self) -> None:
        """An empty tool_name raises ValueError."""
        with pytest.raises(ValueError, match="tool_name"):
            McpRouteRecord(action_class=PingAction, tool_name="")

    def test_whitespace_only_raises(self) -> None:
        """A whitespace-only tool_name raises ValueError."""
        with pytest.raises(ValueError, match="tool_name"):
            McpRouteRecord(action_class=PingAction, tool_name="   ")

    def test_dot_separated_name(self) -> None:
        """Dot-separated names like 'orders.create' are valid."""
        record = McpRouteRecord(action_class=FullAction, tool_name="orders.create")
        assert record.tool_name == "orders.create"

    def test_single_word_name(self) -> None:
        """Single-word tool names are valid."""
        record = McpRouteRecord(action_class=PingAction, tool_name="ping")
        assert record.tool_name == "ping"

    def test_hyphenated_name(self) -> None:
        """Hyphenated tool names are valid."""
        record = McpRouteRecord(action_class=PingAction, tool_name="system-ping")
        assert record.tool_name == "system-ping"


# ═════════════════════════════════════════════════════════════════════════════
# Description field
# ═════════════════════════════════════════════════════════════════════════════


class TestDescription:
    """Verify description field storage."""

    def test_default_description_empty(self) -> None:
        """Default description is an empty string."""
        record = McpRouteRecord(action_class=PingAction, tool_name="ping")
        assert record.description == ""

    def test_custom_description(self) -> None:
        """A custom description is stored and retrievable."""
        record = McpRouteRecord(
            action_class=PingAction,
            tool_name="ping",
            description="Check if the service is alive",
        )
        assert record.description == "Check if the service is alive"


# ═════════════════════════════════════════════════════════════════════════════
# Type extraction
# ═════════════════════════════════════════════════════════════════════════════


class TestTypeExtraction:
    """Verify params_type and result_type are correctly extracted."""

    def test_ping_action_types(self) -> None:
        """PingAction types are extracted via ForwardRef resolution."""
        record = McpRouteRecord(action_class=PingAction, tool_name="ping")
        assert record.params_type is PingAction.Params
        assert record.result_type is PingAction.Result

    def test_full_action_types(self) -> None:
        """FullAction types are extracted correctly."""
        record = McpRouteRecord(action_class=FullAction, tool_name="orders.create")
        assert record.params_type is FullAction.Params
        assert record.result_type is FullAction.Result

    def test_simple_action_types(self) -> None:
        """SimpleAction types are extracted correctly."""
        record = McpRouteRecord(action_class=SimpleAction, tool_name="simple")
        assert record.params_type is SimpleAction.Params
        assert record.result_type is SimpleAction.Result


# ═════════════════════════════════════════════════════════════════════════════
# Computed properties
# ═════════════════════════════════════════════════════════════════════════════


class TestComputedProperties:
    """Verify effective_request_model and effective_response_model."""

    def test_effective_request_defaults_to_params(self) -> None:
        """When request_model is None, effective_request_model is params_type."""
        record = McpRouteRecord(action_class=PingAction, tool_name="ping")
        assert record.effective_request_model is PingAction.Params

    def test_effective_response_defaults_to_result(self) -> None:
        """When response_model is None, effective_response_model is result_type."""
        record = McpRouteRecord(action_class=PingAction, tool_name="ping")
        assert record.effective_response_model is PingAction.Result


# ═════════════════════════════════════════════════════════════════════════════
# Mapper invariants
# ═════════════════════════════════════════════════════════════════════════════


class TestMapperInvariants:
    """Verify mapper requirements inherited from BaseRouteRecord."""

    def test_different_request_without_mapper_raises(self) -> None:
        """request_model != params_type without params_mapper raises ValueError."""
        with pytest.raises(ValueError, match="params_mapper"):
            McpRouteRecord(
                action_class=PingAction,
                tool_name="ping",
                request_model=_AltRequest,
            )

    def test_different_response_without_mapper_raises(self) -> None:
        """response_model != result_type without response_mapper raises ValueError."""
        with pytest.raises(ValueError, match="response_mapper"):
            McpRouteRecord(
                action_class=PingAction,
                tool_name="ping",
                response_model=_AltResponse,
            )

    def test_different_request_with_mapper_accepted(self) -> None:
        """Providing params_mapper resolves the invariant."""
        record = McpRouteRecord(
            action_class=PingAction,
            tool_name="ping",
            request_model=_AltRequest,
            params_mapper=lambda r: PingAction.Params(),
        )
        assert record.effective_request_model is _AltRequest

    def test_different_response_with_mapper_accepted(self) -> None:
        """Providing response_mapper resolves the invariant."""
        record = McpRouteRecord(
            action_class=PingAction,
            tool_name="ping",
            response_model=_AltResponse,
            response_mapper=lambda r: _AltResponse(),
        )
        assert record.effective_response_model is _AltResponse


# ═════════════════════════════════════════════════════════════════════════════
# Frozen immutability
# ═════════════════════════════════════════════════════════════════════════════


class TestFrozen:
    """Verify that McpRouteRecord is truly frozen after creation."""

    def test_cannot_modify_tool_name(self) -> None:
        """Attempting to change tool_name raises AttributeError."""
        record = McpRouteRecord(action_class=PingAction, tool_name="ping")

        with pytest.raises(AttributeError):
            record.tool_name = "other"  # type: ignore[misc]

    def test_cannot_modify_description(self) -> None:
        """Attempting to change description raises AttributeError."""
        record = McpRouteRecord(action_class=PingAction, tool_name="ping")

        with pytest.raises(AttributeError):
            record.description = "new desc"  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════════
# Inherited action_class validation
# ═════════════════════════════════════════════════════════════════════════════


class TestInheritedValidation:
    """Verify BaseRouteRecord validations apply to McpRouteRecord."""

    def test_non_action_raises(self) -> None:
        """A non-BaseAction class triggers TypeError."""

        class _Plain:
            pass

        with pytest.raises(TypeError, match="BaseAction"):
            McpRouteRecord(action_class=_Plain, tool_name="test")

    def test_action_class_stored(self) -> None:
        """A valid action_class is stored on the record."""
        record = McpRouteRecord(action_class=PingAction, tool_name="ping")
        assert record.action_class is PingAction
