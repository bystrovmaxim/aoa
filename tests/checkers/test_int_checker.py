"""
Тесты для IntFieldChecker.

Проверяем:
- Валидные целые числа
- Обязательные и необязательные поля
- Диапазоны значений (min, max)
- Неверные типы (float, string)
"""

import pytest

from action_machine.Checkers.IntFieldChecker import IntFieldChecker
from action_machine.Core.Exceptions import ValidationFieldException


class TestIntFieldChecker:
    """Тесты для целочисленного чекера."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Валидные значения
    # ------------------------------------------------------------------

    def test_int_valid(self, valid_int_params):
        """Корректное целое число проходит проверку."""
        checker = IntFieldChecker("age", "Возраст")
        checker.check(valid_int_params)

    def test_int_valid_zero(self):
        """Ноль — допустимое целое число."""
        checker = IntFieldChecker("value", "Значение")
        params = {"value": 0}
        checker.check(params)

    def test_int_valid_negative(self):
        """Отрицательные числа допустимы, если не задан min_value."""
        checker = IntFieldChecker("value", "Значение")
        params = {"value": -42}
        checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Обязательность
    # ------------------------------------------------------------------

    def test_int_required_missing(self):
        """Обязательное поле отсутствует -> ошибка."""
        checker = IntFieldChecker("age", "Возраст", required=True)
        params = {}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "Отсутствует обязательный параметр: 'age'" in str(exc.value)

    def test_int_required_with_none(self):
        """Обязательное поле с None -> ошибка."""
        checker = IntFieldChecker("age", "Возраст", required=True)
        params = {"age": None}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "Отсутствует обязательный параметр: 'age'" in str(exc.value)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Неверный тип
    # ------------------------------------------------------------------

    def test_int_wrong_type(self, wrong_type_int_params):
        """Неверный тип данных."""
        checker = IntFieldChecker("age", "Возраст")
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(wrong_type_int_params)
        assert "должен быть целым числом" in str(exc.value)

    def test_int_float_passed(self):
        """Передача float вместо int -> ошибка."""
        checker = IntFieldChecker("age", "Возраст")
        params = {"age": 25.5}
        with pytest.raises(ValidationFieldException):
            checker.check(params)

    def test_int_string_passed(self):
        """Передача строки вместо int -> ошибка."""
        checker = IntFieldChecker("age", "Возраст")
        params = {"age": "25"}
        with pytest.raises(ValidationFieldException):
            checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Минимальное значение
    # ------------------------------------------------------------------

    def test_int_min_value(self):
        """Проверка минимального значения."""
        checker = IntFieldChecker("age", "Возраст", min_value=18)

        # Меньше минимума
        params = {"age": 15}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "должен быть не меньше 18" in str(exc.value)

        # Равно минимуму
        params = {"age": 18}
        checker.check(params)

        # Больше минимума
        params = {"age": 25}
        checker.check(params)

    def test_int_min_value_negative(self):
        """Минимальное значение может быть отрицательным."""
        checker = IntFieldChecker("temp", "Температура", min_value=-10)

        params = {"temp": -15}
        with pytest.raises(ValidationFieldException):
            checker.check(params)

        params = {"temp": -10}
        checker.check(params)

        params = {"temp": -5}
        checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Максимальное значение
    # ------------------------------------------------------------------

    def test_int_max_value(self):
        """Проверка максимального значения."""
        checker = IntFieldChecker("age", "Возраст", max_value=100)

        # Больше максимума
        params = {"age": 150}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "должен быть не больше 100" in str(exc.value)

        # Равно максимуму
        params = {"age": 100}
        checker.check(params)

        # Меньше максимума
        params = {"age": 50}
        checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Диапазон значений
    # ------------------------------------------------------------------

    def test_int_range(self):
        """Проверка диапазона."""
        checker = IntFieldChecker("score", "Счёт", min_value=0, max_value=10)

        # Ниже минимума
        params = {"score": -1}
        with pytest.raises(ValidationFieldException):
            checker.check(params)

        # В диапазоне
        params = {"score": 5}
        checker.check(params)

        # Выше максимума
        params = {"score": 11}
        with pytest.raises(ValidationFieldException):
            checker.check(params)

    def test_int_range_inclusive(self):
        """Границы диапазона включены."""
        checker = IntFieldChecker("score", "Счёт", min_value=0, max_value=10)

        # Минимальное значение
        params = {"score": 0}
        checker.check(params)

        # Максимальное значение
        params = {"score": 10}
        checker.check(params)
