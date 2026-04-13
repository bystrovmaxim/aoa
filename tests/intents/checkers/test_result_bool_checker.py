# tests/intents/checkers/test_result_bool_checker.py
"""
Тесты ResultBoolChecker — чекер булевых полей результата аспекта.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что ResultBoolChecker корректно валидирует булевые значения
в словаре результата аспекта. Принимает только True и False —
числа (0, 1), строки ("true", "false") и другие типы отклоняются.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

TestValidValues
    - True и False принимаются без ошибок.

TestInvalidValues
    - Целые числа (0, 1) — не bool, ошибка.
    - Строки ("true", "false") — не bool, ошибка.
    - None при required=True — ошибка (поле обязательно).
    - Список, словарь — не bool, ошибка.

TestRequired
    - required=True: отсутствующее или None поле вызывает ошибку.
    - required=False: отсутствующее или None поле допускается.
    - required=False: присутствующее не-bool поле всё равно вызывает ошибку.

TestDecorator
    - result_bool записывает _checker_meta в функцию.
    - Параметры checker_class, field_name, required сохраняются корректно.
    - Декоратор возвращает оригинальную функцию без изменений.
    - Несколько декораторов на одном методе — список растёт.
"""

import pytest

from action_machine.intents.checkers.result_bool_checker import ResultBoolChecker, result_bool
from action_machine.model.exceptions import ValidationFieldError

# ═════════════════════════════════════════════════════════════════════════════
# Валидные значения
# ═════════════════════════════════════════════════════════════════════════════


class TestValidValues:
    """Проверяет, что True и False принимаются без ошибок."""

    def test_true_accepted(self):
        """True — валидное булево значение."""
        # Arrange
        checker = ResultBoolChecker("is_active", required=True)

        # Act & Assert — исключения нет
        checker.check({"is_active": True})

    def test_false_accepted(self):
        """False — валидное булево значение."""
        # Arrange
        checker = ResultBoolChecker("is_deleted", required=True)

        # Act & Assert — исключения нет
        checker.check({"is_deleted": False})


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные значения
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidValues:
    """Проверяет отклонение не-bool типов с выбросом ValidationFieldError."""

    def test_int_zero_rejected(self):
        """Целое число 0 — не bool, хотя falsy."""
        # Arrange
        checker = ResultBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": 0})

    def test_int_one_rejected(self):
        """Целое число 1 — не bool, хотя truthy."""
        # Arrange
        checker = ResultBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": 1})

    def test_string_true_rejected(self):
        """Строка 'true' — не bool."""
        # Arrange
        checker = ResultBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": "true"})

    def test_string_false_rejected(self):
        """Строка 'false' — не bool."""
        # Arrange
        checker = ResultBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": "false"})

    def test_list_rejected(self):
        """Список — не bool."""
        # Arrange
        checker = ResultBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": [True]})

    def test_dict_rejected(self):
        """Словарь — не bool."""
        # Arrange
        checker = ResultBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": {"value": True}})

    def test_none_rejected_when_required(self):
        """None при required=True вызывает ошибку."""
        # Arrange
        checker = ResultBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": None})

    def test_error_message_contains_field_name(self):
        """Сообщение об ошибке содержит имя поля."""
        # Arrange
        checker = ResultBoolChecker("is_valid", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="is_valid"):
            checker.check({"is_valid": "yes"})

    def test_error_message_contains_actual_type(self):
        """Сообщение об ошибке содержит фактический тип значения."""
        # Arrange
        checker = ResultBoolChecker("is_valid", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="str"):
            checker.check({"is_valid": "yes"})


# ═════════════════════════════════════════════════════════════════════════════
# Обязательность поля (required)
# ═════════════════════════════════════════════════════════════════════════════


class TestRequired:
    """Проверяет поведение флага required для обязательных и опциональных полей."""

    def test_required_missing_field_raises(self):
        """Отсутствующее обязательное поле вызывает ошибку."""
        # Arrange
        checker = ResultBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({})

    def test_required_none_raises(self):
        """None в обязательном поле вызывает ошибку."""
        # Arrange
        checker = ResultBoolChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": None})

    def test_optional_missing_field_passes(self):
        """Отсутствующее опциональное поле допускается."""
        # Arrange
        checker = ResultBoolChecker("flag", required=False)

        # Act & Assert — исключения нет
        checker.check({})

    def test_optional_none_passes(self):
        """None в опциональном поле допускается."""
        # Arrange
        checker = ResultBoolChecker("flag", required=False)

        # Act & Assert — исключения нет
        checker.check({"flag": None})

    def test_optional_invalid_type_still_raises(self):
        """Даже в опциональном поле не-bool значение вызывает ошибку."""
        # Arrange
        checker = ResultBoolChecker("flag", required=False)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"flag": "true"})


# ═════════════════════════════════════════════════════════════════════════════
# Декоратор result_bool
# ═════════════════════════════════════════════════════════════════════════════


class TestDecorator:
    """Проверяет, что декоратор result_bool записывает метаданные в функцию."""

    def test_checker_meta_attached(self):
        """Декоратор создаёт атрибут _checker_meta."""
        # Arrange & Act
        @result_bool("is_active")
        async def aspect(self, params, state, box, connections):
            return {"is_active": True}

        # Assert
        assert hasattr(aspect, "_checker_meta")
        assert len(aspect._checker_meta) == 1

    def test_checker_class_is_result_bool_checker(self):
        """Метаданные содержат правильный класс чекера."""
        # Arrange & Act
        @result_bool("is_active")
        async def aspect(self, params, state, box, connections):
            return {"is_active": True}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["checker_class"] is ResultBoolChecker

    def test_field_name_recorded(self):
        """Имя поля сохраняется в метаданных."""
        # Arrange & Act
        @result_bool("is_deleted")
        async def aspect(self, params, state, box, connections):
            return {"is_deleted": False}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["field_name"] == "is_deleted"

    def test_required_default_true(self):
        """По умолчанию required=True."""
        # Arrange & Act
        @result_bool("flag")
        async def aspect(self, params, state, box, connections):
            return {"flag": True}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["required"] is True

    def test_required_false_recorded(self):
        """Явное required=False сохраняется."""
        # Arrange & Act
        @result_bool("flag", required=False)
        async def aspect(self, params, state, box, connections):
            return {"flag": True}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["required"] is False

    def test_decorator_returns_original_function(self):
        """Декоратор возвращает оригинальную функцию без изменений."""
        # Arrange
        async def original(self, params, state, box, connections):
            return {"flag": True}

        # Act
        decorated = result_bool("flag")(original)

        # Assert
        assert decorated is original

    def test_multiple_decorators_accumulate(self):
        """Несколько декораторов на одном методе создают список метаданных."""
        # Arrange & Act
        @result_bool("is_active")
        @result_bool("is_verified")
        async def aspect(self, params, state, box, connections):
            return {"is_active": True, "is_verified": False}

        # Assert
        assert len(aspect._checker_meta) == 2
        field_names = {m["field_name"] for m in aspect._checker_meta}
        assert field_names == {"is_active", "is_verified"}
