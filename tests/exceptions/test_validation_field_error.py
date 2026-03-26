# tests/exceptions/test_validation_field_error.py
"""
Тесты исключения ValidationFieldError.

Проверяем:
- Хранение поля field при передаче
- Значение field по умолчанию None
"""

from action_machine.core.exceptions import ValidationFieldError


class TestValidationFieldError:
    """Тесты для ValidationFieldError."""

    def test_field_is_set_when_provided(self):
        """Если field передан в конструктор, он сохраняется."""
        exc = ValidationFieldError("Ошибка", field="username")
        assert exc.field == "username"

    def test_field_defaults_to_none(self):
        """Если field не передан, он равен None."""
        exc = ValidationFieldError("Ошибка")
        assert exc.field is None