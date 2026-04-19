# tests/runtime/test_toolsbox_context_privacy.py
"""
Tests for context privacy in ToolsBox.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Checks the key invariant: ToolsBox does NOT expose execution Context publicly [1].
Aspects receive context data only through ContextView, built by the machine when
@context_requires is present [1].

Also verifies ToolsBox frozen semantics: setattr and delattr are forbidden after
construction.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.context.context import Context
from action_machine.logging.scoped_logger import ScopedLogger
from action_machine.runtime.tools_box import ToolsBox

# ═════════════════════════════════════════════════════════════════════════════
# ToolsBox fixture
# ═════════════════════════════════════════════════════════════════════════════

def _make_toolsbox() -> ToolsBox:
    """
    Build ToolsBox with minimal stubs for testing.

    ``Context`` is not stored on the instance; dependencies (run_child, factory, log)
    are mocked.
    """
    return ToolsBox(
        run_child=AsyncMock(),
        factory=DependencyFactory(()),
        resources=None,
        log=MagicMock(spec=ScopedLogger),
        nested_level=0,
        rollup=False,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Context privacy
# ═════════════════════════════════════════════════════════════════════════════

class TestToolsBoxContextPrivacy:
    """No public Context access through ToolsBox."""

    def test_no_context_attribute(self) -> None:
        """box.context does not exist — AttributeError."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert — direct context access forbidden
        with pytest.raises(AttributeError):
            _ = box.context  # type: ignore[attr-defined]

    def test_no_context_in_dir(self) -> None:
        """dir(box) has no bare 'context' name."""
        # Arrange
        box = _make_toolsbox()

        # Act
        public_attrs = [name for name in dir(box) if not name.startswith("_")]

        # Assert
        assert "context" not in public_attrs

    def test_no_get_context_method(self) -> None:
        """get_context() does not exist."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        assert not hasattr(box, "get_context")

    def test_no_ctx_attribute(self) -> None:
        """box.ctx does not exist."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        assert not hasattr(box, "ctx")

    def test_getitem_context_raises(self) -> None:
        """box["context"] does not return Context."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert — ToolsBox is not BaseSchema and has no __getitem__
        with pytest.raises((TypeError, KeyError, AttributeError)):
            _ = box["context"]  # type: ignore[index]

    def test_public_properties_do_not_leak_context(self) -> None:
        """No public property returns a Context instance."""
        # Arrange
        box = _make_toolsbox()

        # Act — collect public property values
        public_names = [name for name in dir(box) if not name.startswith("_")]
        public_values = []
        for name in public_names:
            try:
                val = getattr(box, name)
                if not callable(val):
                    public_values.append(val)
            except Exception:
                pass

        # Assert
        for val in public_values:
            assert not isinstance(val, Context), (
                f"Public property returned Context: {val!r}"
            )

    def test_context_not_stored_on_box_instance(self) -> None:
        """
        ``Context`` is not kept on ``ToolsBox`` (no ``_ToolsBox__context`` or similar).

        Aspects cannot recover execution context from ``box``; only ``ContextView``
        (when declared) or the logger's internal reference applies.
        """
        box = _make_toolsbox()
        assert not hasattr(box, "_ToolsBox__context")
        with pytest.raises(AttributeError):
            object.__getattribute__(box, "_ToolsBox__context")


# ═════════════════════════════════════════════════════════════════════════════
# ToolsBox frozen semantics
# ═════════════════════════════════════════════════════════════════════════════

class TestToolsBoxFrozen:
    """ToolsBox immutability after creation."""

    def test_setattr_raises(self) -> None:
        """Attribute assignment forbidden — AttributeError."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        with pytest.raises(AttributeError, match="frozen"):
            box.custom_attr = "value"  # type: ignore[misc]

    def test_delattr_raises(self) -> None:
        """Attribute deletion forbidden — AttributeError."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        with pytest.raises(AttributeError, match="frozen"):
            del box.nested_level  # type: ignore[misc]

    def test_cannot_overwrite_factory(self) -> None:
        """Cannot replace factory after creation."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        with pytest.raises(AttributeError, match="frozen"):
            box.factory = DependencyFactory(())  # type: ignore[misc]

    def test_cannot_add_context_property(self) -> None:
        """Cannot add a context attribute on the instance."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert — __slots__ + __setattr__ forbid
        with pytest.raises(AttributeError):
            box.context = Context()  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════════
# Public properties behave correctly
# ═════════════════════════════════════════════════════════════════════════════

class TestToolsBoxPublicAPI:
    """Public ToolsBox properties."""

    def test_nested_level(self) -> None:
        """nested_level returns nesting depth."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        assert box.nested_level == 0

    def test_rollup(self) -> None:
        """rollup returns auto-rollback flag."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        assert box.rollup is False

    def test_factory(self) -> None:
        """factory returns DependencyFactory."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        assert isinstance(box.factory, DependencyFactory)

    def test_resources_none(self) -> None:
        """resources is None when not passed."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        assert box.resources is None

    def test_run_child(self) -> None:
        """run_child returns a callable (closure)."""
        # Arrange
        box = _make_toolsbox()

        # Act & Assert
        assert callable(box.run_child)
