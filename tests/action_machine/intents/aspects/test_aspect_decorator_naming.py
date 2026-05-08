# tests/intents/aspects/test_aspect_decorator_naming.py
"""
Naming and validation for ``@regular_aspect`` and ``@summary_aspect``.

Method names must end with ``_aspect`` / ``_summary`` (or ``summary`` for summary).
Empty descriptions are rejected.
"""

import pytest

from aoa.action_machine.exceptions import NamingSuffixError


class TestRegularAspectSuffix:
    """Methods with @regular_aspect must end with '_aspect'."""

    def test_correct_suffix_passes(self) -> None:
        """Name 'validate_data_aspect' — decorator applies without error."""
        from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect

        @regular_aspect("Data validation")
        async def validate_data_aspect(self, params, state, box, connections):
            return {}

        assert hasattr(validate_data_aspect, "_new_aspect_meta")

    def test_missing_suffix_raises(self) -> None:
        """Name 'validate_data' without '_aspect' → NamingSuffixError."""
        from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect

        with pytest.raises(NamingSuffixError, match="_aspect"):
            @regular_aspect("Data validation")
            async def validate_data(self, params, state, box, connections):
                return {}

    def test_wrong_suffix_raises(self) -> None:
        """Name 'validate_data_step' → NamingSuffixError."""
        from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect

        with pytest.raises(NamingSuffixError, match="_aspect"):
            @regular_aspect("Data validation")
            async def validate_data_step(self, params, state, box, connections):
                return {}


class TestSummaryAspectSuffix:
    """Methods with @summary_aspect must end with '_summary' or be named 'summary'."""

    def test_correct_suffix_passes(self) -> None:
        """Name 'build_result_summary' — decorator applies without error."""
        from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect

        @summary_aspect("Building result")
        async def build_result_summary(self, params, state, box, connections):
            pass

        assert hasattr(build_result_summary, "_new_aspect_meta")

    def test_missing_suffix_raises(self) -> None:
        """Name 'build_result' without '_summary' → NamingSuffixError."""
        from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect

        with pytest.raises(NamingSuffixError, match="_summary"):
            @summary_aspect("Building result")
            async def build_result(self, params, state, box, connections):
                pass


class TestAspectDescriptionRequired:
    """Non-empty description for aspect decorators."""

    def test_regular_aspect_empty_description_raises(self) -> None:
        """@regular_aspect("") → ValueError."""
        from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect

        with pytest.raises(ValueError, match="cannot be empty"):
            @regular_aspect("")
            async def validate_aspect(self, params, state, box, connections):
                return {}

    def test_summary_aspect_empty_description_raises(self) -> None:
        """@summary_aspect("") → ValueError."""
        from aoa.action_machine.intents.aspects.summary_aspect_decorator import summary_aspect

        with pytest.raises(ValueError, match="cannot be empty"):
            @summary_aspect("")
            async def result_summary(self, params, state, box, connections):
                pass

    def test_regular_aspect_whitespace_description_raises(self) -> None:
        """@regular_aspect("   ") → ValueError."""
        from aoa.action_machine.intents.aspects.regular_aspect_decorator import regular_aspect

        with pytest.raises(ValueError, match="cannot be empty"):
            @regular_aspect("   ")
            async def validate_aspect(self, params, state, box, connections):
                return {}
