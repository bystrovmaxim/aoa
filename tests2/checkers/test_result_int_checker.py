# tests2/checkers/test_result_int_checker.py
"""
Тесты ResultIntChecker и декоратора result_int — целочисленные поля.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ResultIntChecker проверяет, что поле результата аспекта является целым
числом (int) и лежит в заданном диапазоне (min_value, max_value).

Float, bool и строки не принимаются — только точное isinstance(value, int).
Bool является подклассом int в Python, но ResultIntChecker проверяет
isinstance(value, int), и bool проходит эту проверку. Если нужно
исключить bool — используйте ResultBoolChecker отдельно.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Валидные значения:
    - Положительное int, отрицательное int, ноль.
    - Значение на границе min_value / max_value.

Невалидные значения:
    - Float вместо int → ValidationFieldError.
    - Строка вместо int → ValidationFieldError.
    - Значение меньше min_value → ValidationFieldError.
    - Значение больше max_value → ValidationFieldError.

Required / Optional:
    - required=True, поле отсутствует → ValidationFieldError.
    - required=False, поле отсутствует → OK.

Декоратор:
    - result_int записывает _checker_meta с min_value, max_value.
"""

import pytest

from action_machine.checkers.result_int_checker import ResultIntChecker, result_int
from action_machine.core.exceptions import ValidationFieldError

# ═════════════════════════════════════════════════════════════════════════════
# Валидные значения
# ═════════════════════════════════════════════════════════════════════════════


class TestValidValues:
    """check() проходит для валидных целочисленных значений."""

    def test_positive_int(self) -> None:
        """Положительное целое число проходит."""
        # Arrange
        checker = ResultIntChecker("count", required=True)

        # Act & Assert
        checker.check({"count": 42})

    def test_negative_int(self) -> None:
        """Отрицательное целое число проходит."""
        # Arrange
        checker = ResultIntChecker("offset", required=True)

        # Act & Assert
        checker.check({"offset": -10})

    def test_zero(self) -> None:
        """Ноль проходит — валидное целое число."""
        # Arrange
        checker = ResultIntChecker("count", required=True)

        # Act & Assert
        checker.check({"count": 0})

    def test_exact_min_value(self) -> None:
        """Значение ровно min_value проходит (включительно)."""
        # Arrange
        checker = ResultIntChecker("age", required=True, min_value=0)

        # Act & Assert
        checker.check({"age": 0})

    def test_exact_max_value(self) -> None:
        """Значение ровно max_value проходит (включительно)."""
        # Arrange
        checker = ResultIntChecker("score", required=True, max_value=100)

        # Act & Assert
        checker.check({"score": 100})

    def test_between_min_and_max(self) -> None:
        """Значение между min и max проходит."""
        # Arrange
        checker = ResultIntChecker("level", required=True, min_value=1, max_value=10)

        # Act & Assert
        checker.check({"level": 5})

    def test_large_int(self) -> None:
        """Очень большое целое число проходит."""
        # Arrange
        checker = ResultIntChecker("big", required=True)

        # Act & Assert
        checker.check({"big": 10**18})


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные значения
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidValues:
    """check() бросает ValidationFieldError для невалидных значений."""

    def test_float_raises(self) -> None:
        """Float вместо int → ValidationFieldError."""
        # Arrange
        checker = ResultIntChecker("count", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="целым числом"):
            checker.check({"count": 3.14})

    def test_string_raises(self) -> None:
        """Строка вместо int → ValidationFieldError."""
        # Arrange
        checker = ResultIntChecker("count", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="целым числом"):
            checker.check({"count": "42"})

    def test_list_raises(self) -> None:
        """Список вместо int → ValidationFieldError."""
        # Arrange
        checker = ResultIntChecker("count", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="целым числом"):
            checker.check({"count": [1, 2, 3]})

    def test_below_min_value(self) -> None:
        """Значение меньше min_value → ValidationFieldError."""
        # Arrange
        checker = ResultIntChecker("age", required=True, min_value=0)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="не меньше 0"):
            checker.check({"age": -1})

    def test_above_max_value(self) -> None:
        """Значение больше max_value → ValidationFieldError."""
        # Arrange
        checker = ResultIntChecker("score", required=True, max_value=100)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="не больше 100"):
            checker.check({"score": 101})

    def test_below_min_with_both_bounds(self) -> None:
        """Значение ниже min при заданных min и max."""
        # Arrange
        checker = ResultIntChecker("level", required=True, min_value=1, max_value=10)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="не меньше 1"):
            checker.check({"level": 0})

    def test_above_max_with_both_bounds(self) -> None:
        """Значение выше max при заданных min и max."""
        # Arrange
        checker = ResultIntChecker("level", required=True, min_value=1, max_value=10)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="не больше 10"):
            checker.check({"level": 11})


# ═════════════════════════════════════════════════════════════════════════════
# Required / Optional
# ═════════════════════════════════════════════════════════════════════════════


class TestRequired:
    """Поведение при required=True и required=False."""

    def test_required_missing_raises(self) -> None:
        """required=True, поле отсутствует → ValidationFieldError."""
        # Arrange
        checker = ResultIntChecker("count", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="Отсутствует обязательный"):
            checker.check({})

    def test_required_none_raises(self) -> None:
        """required=True, поле=None → ValidationFieldError."""
        # Arrange
        checker = ResultIntChecker("count", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="Отсутствует обязательный"):
            checker.check({"count": None})

    def test_optional_missing_ok(self) -> None:
        """required=False, поле отсутствует → OK."""
        # Arrange
        checker = ResultIntChecker("count", required=False)

        # Act & Assert
        checker.check({})

    def test_optional_present_still_validated(self) -> None:
        """required=False, но поле присутствует — тип всё равно проверяется."""
        # Arrange
        checker = ResultIntChecker("count", required=False)

        # Act & Assert — строка вместо int → ошибка
        with pytest.raises(ValidationFieldError, match="целым числом"):
            checker.check({"count": "not_int"})


# ═════════════════════════════════════════════════════════════════════════════
# Декоратор result_int
# ═════════════════════════════════════════════════════════════════════════════


class TestDecorator:
    """Функция-декоратор result_int записывает _checker_meta."""

    def test_writes_checker_meta(self) -> None:
        """
        @result_int("count") записывает _checker_meta в метод.
        """
        # Arrange & Act
        @result_int("count", required=True, min_value=0, max_value=1000)
        async def calc(self, params, state, box, connections):
            return {"count": 42}

        # Assert
        assert hasattr(calc, "_checker_meta")
        assert len(calc._checker_meta) == 1
        m = calc._checker_meta[0]
        assert m["checker_class"] is ResultIntChecker
        assert m["field_name"] == "count"
        assert m["required"] is True
        assert m["min_value"] == 0
        assert m["max_value"] == 1000

    def test_decorator_preserves_function(self) -> None:
        """Декоратор возвращает ту же функцию."""
        # Arrange
        async def original(self, params, state, box, connections):
            return {}

        # Act
        decorated = result_int("count")(original)

        # Assert
        assert decorated is original

    def test_default_params(self) -> None:
        """Дефолтные параметры: required=True, min_value=None, max_value=None."""
        # Arrange & Act
        @result_int("count")
        async def calc(self, params, state, box, connections):
            return {"count": 1}

        # Assert
        m = calc._checker_meta[0]
        assert m["required"] is True
        assert m["min_value"] is None
        assert m["max_value"] is None
