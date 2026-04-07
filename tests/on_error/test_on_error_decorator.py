# tests/on_error/test_on_error_decorator.py
"""
Tests for the @on_error decorator.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Verifies the behavior of the @on_error decorator with correct and incorrect
arguments and method signatures.

The file contains tests for negative scenarios, so all functions are created
inside test methods and are not part of the working domain model.
"""

import pytest

from action_machine.core.exceptions import NamingSuffixError
from action_machine.on_error import on_error

# ═════════════════════════════════════════════════════════════════════════════
# Successful decoration
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorDecoratorSuccess:
    """Tests for successful application of @on_error to correct methods."""

    def test_single_exception_type(self) -> None:
        """Single exception type → method is decorated, _on_error_meta contains a tuple with one type."""

        # Arrange — define an async method with correct signature and suffix
        @on_error(ValueError, description="Handling ValueError")
        async def handle_value_on_error(self, params, state, box, connections, error):
            pass

        # Assert — metadata is recorded correctly
        assert hasattr(handle_value_on_error, "_on_error_meta")
        meta = handle_value_on_error._on_error_meta
        assert meta["exception_types"] == (ValueError,)
        assert meta["description"] == "Handling ValueError"

    def test_tuple_of_exception_types(self) -> None:
        """Tuple of exception types → all types are saved in _on_error_meta."""

        # Arrange — tuple of two types
        @on_error((ValueError, TypeError), description="Handling multiple types")
        async def handle_multi_on_error(self, params, state, box, connections, error):
            pass

        # Assert — both types in the tuple
        meta = handle_multi_on_error._on_error_meta
        assert meta["exception_types"] == (ValueError, TypeError)
        assert meta["description"] == "Handling multiple types"

    def test_custom_exception_type(self) -> None:
        """Custom exception type (Exception subclass) → accepted."""

        # Arrange — define a custom error class and async method
        class MyCustomError(Exception):
            pass

        @on_error(MyCustomError, description="Custom error")
        async def handle_custom_on_error(self, params, state, box, connections, error):
            pass

        # Assert — metadata should contain exactly the custom type
        meta = handle_custom_on_error._on_error_meta
        assert meta["exception_types"] == (MyCustomError,)

    def test_method_returns_unchanged(self) -> None:
        """Decorator returns the same function object without wrapping."""

        # Arrange — define the original async function
        async def original_on_error(self, params, state, box, connections, error):
            pass

        # Act — apply the decorator to the function
        decorated = on_error(ValueError, description="Test")(original_on_error)

        # Assert — decorator does not wrap the function, returns the same object
        assert decorated is original_on_error


# ═════════════════════════════════════════════════════════════════════════════
# Exception type errors
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorExceptionTypeErrors:
    """Tests for errors with incorrect exception types."""

    def test_not_a_type(self) -> None:
        """String instead of type → TypeError."""

        # Act — call the decorator with incorrect first argument
        # Assert — expect error about invalid exception type
        with pytest.raises(TypeError, match="должен быть типом Exception"):
            on_error("ValueError", description="Тест")  # type: ignore[arg-type]

    def test_not_exception_subclass(self) -> None:
        """Type not inheriting from Exception → TypeError."""

        # Act — pass a class that does not inherit from Exception
        # Assert — expect error about incompatibility with Exception
        with pytest.raises(TypeError, match="не является подклассом Exception"):
            on_error(int, description="Тест")  # type: ignore[arg-type]

    def test_empty_tuple(self) -> None:
        """Empty tuple of types → TypeError."""

        # Act & Assert
        with pytest.raises(TypeError, match="пустой кортеж"):
            on_error((), description="Тест")

    def test_tuple_with_non_type(self) -> None:
        """Tuple with non-type inside → TypeError."""

        # Act & Assert
        with pytest.raises(TypeError, match="не является типом"):
            on_error((ValueError, "not_a_type"), description="Тест")  # type: ignore[arg-type]

    def test_tuple_with_non_exception(self) -> None:
        """Tuple with type not inheriting from Exception → TypeError."""

        # Act & Assert
        with pytest.raises(TypeError, match="не является подклассом Exception"):
            on_error((ValueError, int), description="Тест")  # type: ignore[arg-type]

    def test_integer_instead_of_type(self) -> None:
        """Number instead of type → TypeError."""

        # Act & Assert
        with pytest.raises(TypeError, match="должен быть типом Exception"):
            on_error(42, description="Тест")  # type: ignore[arg-type]


# ═════════════════════════════════════════════════════════════════════════════
# Description errors
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorDescriptionErrors:
    """Tests for errors with incorrect description."""

    def test_description_not_string(self) -> None:
        """Number instead of string for description → TypeError."""

        # Act & Assert
        with pytest.raises(TypeError, match="description должен быть строкой"):
            on_error(ValueError, description=42)  # type: ignore[arg-type]

    def test_description_empty(self) -> None:
        """Empty string for description → ValueError."""

        # Act & Assert
        with pytest.raises(ValueError, match="не может быть пустой"):
            on_error(ValueError, description="")

    def test_description_whitespace_only(self) -> None:
        """String of whitespace only in description → ValueError."""

        # Act & Assert
        with pytest.raises(ValueError, match="не может быть пустой"):
            on_error(ValueError, description="   ")


# ═════════════════════════════════════════════════════════════════════════════
# Method errors
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorMethodErrors:
    """Tests for errors with incorrect decorated method."""

    def test_not_callable(self) -> None:
        """Application to non-callable → TypeError."""

        # Act & Assert
        with pytest.raises(TypeError, match="только к методам"):
            on_error(ValueError, description="Тест")(42)

    def test_sync_method(self) -> None:
        """Synchronous method → TypeError."""

        # Arrange — synchronous function
        def sync_on_error(self, params, state, box, connections, error):
            pass

        # Act & Assert
        with pytest.raises(TypeError, match="асинхронным"):
            on_error(ValueError, description="Тест")(sync_on_error)

    def test_wrong_param_count_too_few(self) -> None:
        """Fewer than 6 parameters → TypeError."""

        # Arrange — 5 parameters instead of 6
        async def short_on_error(self, params, state, box, connections):
            pass

        # Act & Assert
        with pytest.raises(TypeError, match="6 параметров"):
            on_error(ValueError, description="Тест")(short_on_error)

    def test_wrong_param_count_too_many(self) -> None:
        """More than 6 parameters → TypeError."""

        # Arrange — 7 parameters
        async def long_on_error(self, params, state, box, connections, error, extra):
            pass

        # Act & Assert
        with pytest.raises(TypeError, match="6 параметров"):
            on_error(ValueError, description="Тест")(long_on_error)


# ═════════════════════════════════════════════════════════════════════════════
# Naming suffix errors
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorNamingSuffix:
    """Tests for checking the '_on_error' suffix in the method name."""

    def test_missing_suffix(self) -> None:
        """Name without '_on_error' suffix → NamingSuffixError."""

        # Arrange — method with correct signature but without suffix
        async def handle_validation(self, params, state, box, connections, error):
            pass

        # Act & Assert
        with pytest.raises(NamingSuffixError, match="_on_error"):
            on_error(ValueError, description="Тест")(handle_validation)

    def test_wrong_suffix(self) -> None:
        """Name with wrong suffix → NamingSuffixError."""

        # Arrange — suffix "_handler" instead of "_on_error"
        async def handle_validation_handler(self, params, state, box, connections, error):
            pass

        # Act & Assert
        with pytest.raises(NamingSuffixError, match="_on_error"):
            on_error(ValueError, description="Тест")(handle_validation_handler)

    def test_correct_suffix_passes(self) -> None:
        """Name with correct suffix → decorator applies without errors."""

        # Arrange & Act — suffix "_on_error" is correct
        @on_error(ValueError, description="Suffix test")
        async def handle_validation_on_error(self, params, state, box, connections, error):
            pass

        # Assert — metadata is recorded
        assert hasattr(handle_validation_on_error, "_on_error_meta")
