# tests/intents/logging/test_log_scope.py
"""Tests LogScope, an object that describes a location in the execution pipeline.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

LogScope is an object that stores information about the logger calling context:
in which action, aspect, plugin, at what nesting level
and at what event logging occurs [1].

The values ​​are passed as kwargs and become instance attributes [3].
LogScope is not a pydantic model and does not inherit from BaseSchema [3].
It is a lightweight object with dynamic attributes and dict-like access
via __getitem__[3].

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCOPE FIELDS
═══════════════════ ════════════════════ ════════════════════ ════════════════════

For action aspects:
    machine, action, aspect, nest_level

For plugins:
    machine, plugin, action, event, nest_level

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

- as_dotpath() returns all non-empty string values, joined by dots.
- The order of the keys is preserved, empty values ​​are skipped.
- The result is cached after the first call.
- Dict-like access (__getitem__, __contains__, get, keys, values, items) [3].
- to_dict() returns a copy of all fields."""

import pytest

from action_machine.logging.log_scope import LogScope

# ======================================================================
#TESTS: as_dotpath()
# ======================================================================

class TestAsDotpath:
    """The as_dotpath() method generates a string from all non-empty fields."""

    def test_single_key(self) -> None:
        """One key -> just a value."""
        # Arrange
        scope = LogScope(action="ProcessOrderAction")

        # Act
        result = scope.as_dotpath()

        # Assert
        assert result == "ProcessOrderAction"

    def test_multiple_keys(self) -> None:
        """Multiple keys → values ​​separated by a dot."""
        # Arrange
        scope = LogScope(
            action="ProcessOrderAction",
            aspect="validate_user",
            event="before",
        )

        # Act
        result = scope.as_dotpath()

        # Assert
        assert result == "ProcessOrderAction.validate_user.before"

    def test_skips_empty_values(self) -> None:
        """Empty lines and None are skipped."""
        # Arrange
        scope = LogScope(
            action="MyAction",
            aspect="",
            event="start",
            extra=None,
        )

        # Act
        result = scope.as_dotpath()

        #Assert - aspect omitted, extra omitted
        assert result == "MyAction.start"

    def test_preserves_order(self) -> None:
        """The order of the keys matches the order of the kwargs when created."""
        # Arrange
        scope = LogScope(first="1", second="2", third="3")

        # Act
        result = scope.as_dotpath()

        # Assert
        assert result == "1.2.3"

    def test_caches_result(self) -> None:
        """The result is cached after the first call."""
        # Arrange
        scope = LogScope(action="MyAction", aspect="load")

        # Act
        first = scope.as_dotpath()
        second = scope.as_dotpath()

        # Assert
        assert first == "MyAction.load"
        assert second == "MyAction.load"
        assert first is second
        assert scope._cached_path == "MyAction.load"

    def test_empty_scope(self) -> None:
        """Empty scope → empty string."""
        # Arrange
        scope = LogScope()

        # Act
        result = scope.as_dotpath()

        # Assert
        assert result == ""

    def test_scope_with_unicode(self) -> None:
        """Unicode characters are included correctly in dotpath."""
        # Arrange
        scope = LogScope(action="action", event="🚀 start")

        # Act
        result = scope.as_dotpath()

        # Assert
        assert "action" in result
        assert "🚀" in result

    def test_scope_with_special_characters(self) -> None:
        """Special characters (dots, slashes) are not treated specially."""
        # Arrange
        scope = LogScope(action="Test.Action", event="before:start", path="/api/v1/test")

        # Act
        result = scope.as_dotpath()

        # Assert
        assert result == "Test.Action.before:start./api/v1/test"


# ======================================================================
#TESTS: Dict-like access (LogScope)
# ======================================================================

class TestDictAccess:
    """LogScope supports dict-like access via __getitem__."""

    def test_getitem(self) -> None:
        """__getitem__ returns the value of the field."""
        # Arrange
        scope = LogScope(action="MyAction")

        # Act & Assert
        assert scope["action"] == "MyAction"

    def test_getitem_missing_raises_key_error(self) -> None:
        """Non-existent key → KeyError."""
        # Arrange
        scope = LogScope(action="MyAction")

        # Act & Assert
        with pytest.raises(KeyError):
            _ = scope["missing"]

    def test_contains(self) -> None:
        """The in operator checks for the presence of an attribute."""
        # Arrange
        scope = LogScope(action="MyAction", aspect="load")

        # Act & Assert
        assert "action" in scope
        assert "aspect" in scope
        assert "missing" not in scope

    def test_get_with_default(self) -> None:
        """get() returns value or default."""
        # Arrange
        scope = LogScope(action="MyAction")

        # Act & Assert
        assert scope.get("action") == "MyAction"
        assert scope.get("missing", "fallback") == "fallback"
        assert scope.get("missing") is None

    def test_keys(self) -> None:
        """keys() returns a list of public field names."""
        # Arrange
        scope = LogScope(action="A", aspect="B", event="C")

        # Act
        keys = scope.keys()

        # Assert
        assert set(keys) == {"action", "aspect", "event"}

    def test_values(self) -> None:
        """values() returns a list of values."""
        # Arrange
        scope = LogScope(action="A", aspect="B", event="C")

        # Act
        values = scope.values()

        # Assert
        assert set(values) == {"A", "B", "C"}

    def test_items(self) -> None:
        """items() returns (key, value) pairs."""
        # Arrange
        scope = LogScope(action="A", aspect="B", event="C")

        # Act
        items = scope.items()

        # Assert
        assert len(items) == 3
        assert ("action", "A") in items
        assert ("aspect", "B") in items
        assert ("event", "C") in items


# ======================================================================
#TESTS: to_dict()
# ======================================================================

class TestToDict:
    """to_dict() returns a copy of all fields."""

    def test_returns_copy(self) -> None:
        """to_dict() returns a new dictionary, changes do not affect scope."""
        # Arrange
        scope = LogScope(action="MyAction")

        # Act
        d = scope.to_dict()
        d["action"] = "Modified"

        # Assert
        assert scope["action"] == "MyAction"
        assert d["action"] == "Modified"

    def test_includes_all_fields(self) -> None:
        """to_dict() includes all passed fields."""
        # Arrange
        scope = LogScope(action="A", aspect="B", event="C", nest_level=2)

        # Act
        d = scope.to_dict()

        # Assert
        assert d == {"action": "A", "aspect": "B", "event": "C", "nest_level": 2}


# ======================================================================
#TESTS: Various scope configurations
# ======================================================================

class TestDifferentScopes:
    """Various sets of fields for scope."""

    def test_aspect_scope(self) -> None:
        """Scope for the action aspect."""
        # Arrange & Act
        scope = LogScope(
            machine="ActionProductMachine",
            action="module.CreateOrderAction",
            aspect="process_payment",
            nest_level=0,
        )

        # Assert
        assert scope.as_dotpath() == "ActionProductMachine.module.CreateOrderAction.process_payment.0"
        assert scope["machine"] == "ActionProductMachine"
        assert scope["aspect"] == "process_payment"

    def test_plugin_scope(self) -> None:
        """Scope for the plugin handler."""
        # Arrange & Act
        scope = LogScope(
            machine="ActionProductMachine",
            plugin="MetricsPlugin",
            action="module.CreateOrderAction",
            event="global_finish",
            nest_level=1,
        )

        # Assert
        assert scope.as_dotpath() == "ActionProductMachine.MetricsPlugin.module.CreateOrderAction.global_finish.1"
        assert "plugin" in scope
        assert "event" in scope
        assert "aspect" not in scope

    def test_empty_string_key(self) -> None:
        """An empty string value is passed through the dotpath, but the field exists."""
        # Arrange
        scope = LogScope(action="", event="start")

        # Act
        dotpath = scope.as_dotpath()

        #Assert - action is skipped, event remains
        assert dotpath == "start"
        assert "action" in scope
        assert scope["action"] == ""

    def test_none_key(self) -> None:
        """The None value is skipped in dotpath."""
        # Arrange
        scope = LogScope(action="MyAction", aspect=None, event="start")

        # Act
        dotpath = scope.as_dotpath()

        #Assert - aspect omitted
        assert dotpath == "MyAction.start"
        assert dotpath == "MyAction.start"
