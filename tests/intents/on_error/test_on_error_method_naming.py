# tests/intents/on_error/test_on_error_method_naming.py
"""
Naming and description validation for ``@on_error`` handlers.

Method names must end with ``_on_error``. Description must be non-empty where required.
"""

import pytest

from action_machine.exceptions import NamingSuffixError


class TestOnErrorSuffix:
    """Methods with @on_error must end with '_on_error'."""

    def test_correct_suffix_passes(self) -> None:
        """Name 'handle_validation_on_error' — decorator applies."""
        from action_machine.intents.on_error import on_error

        @on_error(ValueError, description="Validation error")
        async def handle_validation_on_error(self, params, state, box, connections, error):
            pass

        assert hasattr(handle_validation_on_error, "_on_error_meta")

    def test_missing_suffix_raises(self) -> None:
        """Name 'handle_validation' without '_on_error' → NamingSuffixError."""
        from action_machine.intents.on_error import on_error

        with pytest.raises(NamingSuffixError, match="_on_error"):
            @on_error(ValueError, description="Validation error")
            async def handle_validation(self, params, state, box, connections, error):
                pass


class TestOnErrorDescriptionRequired:
    """@on_error rejects an empty description string."""

    def test_on_error_empty_description_raises(self) -> None:
        """@on_error(ValueError, description="") → ValueError."""
        from action_machine.intents.on_error import on_error

        with pytest.raises(ValueError, match="cannot be empty"):
            on_error(ValueError, description="")
