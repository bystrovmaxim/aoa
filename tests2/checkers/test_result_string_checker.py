# tests2/checkers/test_result_string_checker.py
"""
Тесты ResultStringChecker и декоратора result_string — строковые поля.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ResultStringChecker проверяет, что поле результата аспекта является строкой
и удовлетворяет ограничениям: not_empty, min_length, max_length.

Функция-декоратор result_string применяется к методу-аспекту и записывает
метаданные чекера в _checker_meta. MetadataBuilder собирает их в
ClassMetadata.checkers.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Валидные значения:
    - Обычная строка проходит проверку.
    - Пустая строка проходит (если not_empty=False).
    - Строка нужной длины проходит min_length/max_length.

Невалидные значения:
    - Не строка (int, list, None) → ValidationFieldError.
    - Пустая строка при not_empty=True → ValidationFieldError.
    - Строка короче min_length → ValidationFieldError.
    - Строка длиннее max_length → ValidationFieldError.

Required:
    - required=True, поле отсутствует → ValidationFieldError.
    - required=True, поле None → ValidationFieldError.
    - required=False, поле отсутствует → OK.

Декоратор:
    - result_string записывает _checker_meta в метод.
    - Несколько чекеров на одном методе — все записываются.
"""

import pytest

from action_machine.checkers.result_string_checker import ResultStringChecker, result_string
from action_machine.core.exceptions import ValidationFieldError

# ═════════════════════════════════════════════════════════════════════════════
# Валидные значения
# ═════════════════════════════════════════════════════════════════════════════


class TestValidValues:
    """check() проходит для валидных строковых значений."""

    def test_regular_string(self) -> None:
        """Обычная строка проходит без ограничений."""
        # Arrange
        checker = ResultStringChecker("name", required=True)

        # Act & Assert — не бросает исключение
        checker.check({"name": "Alice"})

    def test_empty_string_allowed_by_default(self) -> None:
        """Пустая строка допустима при not_empty=False (по умолчанию)."""
        # Arrange
        checker = ResultStringChecker("name", required=True, not_empty=False)

        # Act & Assert
        checker.check({"name": ""})

    def test_min_length_exact(self) -> None:
        """Строка длиной ровно min_length проходит."""
        # Arrange
        checker = ResultStringChecker("code", required=True, min_length=3)

        # Act & Assert — "abc" длиной 3 == min_length
        checker.check({"code": "abc"})

    def test_max_length_exact(self) -> None:
        """Строка длиной ровно max_length проходит."""
        # Arrange
        checker = ResultStringChecker("code", required=True, max_length=5)

        # Act & Assert — "abcde" длиной 5 == max_length
        checker.check({"code": "abcde"})

    def test_min_and_max_length(self) -> None:
        """Строка между min_length и max_length проходит."""
        # Arrange
        checker = ResultStringChecker("iso", required=True, min_length=3, max_length=3)

        # Act & Assert — "RUB" длиной 3
        checker.check({"iso": "RUB"})


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные значения
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidValues:
    """check() бросает ValidationFieldError для невалидных значений."""

    def test_not_string_int(self) -> None:
        """Число вместо строки → ValidationFieldError."""
        # Arrange
        checker = ResultStringChecker("name", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="строкой"):
            checker.check({"name": 42})

    def test_not_string_list(self) -> None:
        """Список вместо строки → ValidationFieldError."""
        # Arrange
        checker = ResultStringChecker("name", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="строкой"):
            checker.check({"name": ["a", "b"]})

    def test_not_string_bool(self) -> None:
        """Bool вместо строки → ValidationFieldError."""
        # Arrange
        checker = ResultStringChecker("flag", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="строкой"):
            checker.check({"flag": True})

    def test_not_empty_with_empty_string(self) -> None:
        """Пустая строка при not_empty=True → ValidationFieldError."""
        # Arrange
        checker = ResultStringChecker("name", required=True, not_empty=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="не может быть пустым"):
            checker.check({"name": ""})

    def test_shorter_than_min_length(self) -> None:
        """Строка короче min_length → ValidationFieldError."""
        # Arrange
        checker = ResultStringChecker("code", required=True, min_length=5)

        # Act & Assert — "ab" длиной 2 < min_length=5
        with pytest.raises(ValidationFieldError, match="не меньше 5"):
            checker.check({"code": "ab"})

    def test_longer_than_max_length(self) -> None:
        """Строка длиннее max_length → ValidationFieldError."""
        # Arrange
        checker = ResultStringChecker("code", required=True, max_length=3)

        # Act & Assert — "abcdef" длиной 6 > max_length=3
        with pytest.raises(ValidationFieldError, match="не больше 3"):
            checker.check({"code": "abcdef"})


# ═════════════════════════════════════════════════════════════════════════════
# Required / Optional
# ═════════════════════════════════════════════════════════════════════════════


class TestRequired:
    """Поведение при required=True и required=False."""

    def test_required_missing_field_raises(self) -> None:
        """required=True, поле отсутствует → ValidationFieldError."""
        # Arrange
        checker = ResultStringChecker("name", required=True)

        # Act & Assert — пустой словарь, поля нет
        with pytest.raises(ValidationFieldError, match="Отсутствует обязательный"):
            checker.check({})

    def test_required_none_value_raises(self) -> None:
        """required=True, поле=None → ValidationFieldError."""
        # Arrange
        checker = ResultStringChecker("name", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="Отсутствует обязательный"):
            checker.check({"name": None})

    def test_optional_missing_field_ok(self) -> None:
        """required=False, поле отсутствует → check() проходит без ошибки."""
        # Arrange
        checker = ResultStringChecker("name", required=False)

        # Act & Assert — не бросает
        checker.check({})

    def test_optional_none_value_ok(self) -> None:
        """required=False, поле=None → check() проходит без ошибки."""
        # Arrange
        checker = ResultStringChecker("name", required=False)

        # Act & Assert
        checker.check({"name": None})

    def test_optional_present_still_validated(self) -> None:
        """required=False, но поле присутствует — тип всё равно проверяется."""
        # Arrange
        checker = ResultStringChecker("name", required=False)

        # Act & Assert — int вместо str → ошибка даже для optional
        with pytest.raises(ValidationFieldError, match="строкой"):
            checker.check({"name": 42})


# ═════════════════════════════════════════════════════════════════════════════
# Декоратор result_string
# ═════════════════════════════════════════════════════════════════════════════


class TestDecorator:
    """Функция-декоратор result_string записывает _checker_meta."""

    def test_writes_checker_meta(self) -> None:
        """
        @result_string("name") записывает _checker_meta в метод.

        _checker_meta — список словарей с ключами checker_class,
        field_name, required и дополнительными параметрами.
        """
        # Arrange & Act
        @result_string("name", required=True, min_length=1)
        async def validate(self, params, state, box, connections):
            return {"name": "test"}

        # Assert — _checker_meta записан
        assert hasattr(validate, "_checker_meta")
        assert len(validate._checker_meta) == 1
        meta = validate._checker_meta[0]
        assert meta["checker_class"] is ResultStringChecker
        assert meta["field_name"] == "name"
        assert meta["required"] is True
        assert meta["min_length"] == 1

    def test_multiple_checkers_on_one_method(self) -> None:
        """
        Несколько result_string на одном методе — все записываются в список.

        Один метод может проверять несколько полей.
        """
        # Arrange & Act
        @result_string("first_name", required=True)
        @result_string("last_name", required=True)
        async def validate(self, params, state, box, connections):
            return {"first_name": "John", "last_name": "Doe"}

        # Assert — два чекера в списке
        assert len(validate._checker_meta) == 2
        fields = [m["field_name"] for m in validate._checker_meta]
        assert "first_name" in fields
        assert "last_name" in fields

    def test_decorator_preserves_function(self) -> None:
        """
        Декоратор возвращает ту же функцию — не оборачивает.
        """
        # Arrange
        async def original(self, params, state, box, connections):
            return {}

        # Act
        decorated = result_string("name")(original)

        # Assert
        assert decorated is original

    def test_extra_params_recorded(self) -> None:
        """
        Все параметры (min_length, max_length, not_empty) записываются в meta.
        """
        # Arrange & Act
        @result_string("code", min_length=3, max_length=10, not_empty=True)
        async def validate(self, params, state, box, connections):
            return {"code": "ABC"}

        # Assert
        meta = validate._checker_meta[0]
        assert meta["min_length"] == 3
        assert meta["max_length"] == 10
        assert meta["not_empty"] is True
