"""
Тесты для FloatFieldChecker.

Проверяем:
- Валидные числа (int и float)
- Обязательные и необязательные поля
- Диапазоны значений (min, max)
- Неверные типы (string, bool)
"""

import pytest

from action_machine.Checkers.FloatFieldChecker import FloatFieldChecker
from action_machine.Core.Exceptions import ValidationFieldException


class TestFloatFieldChecker:
    """Тесты для чекера чисел с плавающей точкой."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Валидные значения
    # ------------------------------------------------------------------

    def test_float_valid_int(self, valid_int_params):
        """int принимается как float."""
        checker = FloatFieldChecker("price", "Цена")
        # Передаём params с int
        params = {"price": 100}
        checker.check(params)

    def test_float_valid_float(self, valid_float_params):
        """float проходит."""
        checker = FloatFieldChecker("price", "Цена")
        checker.check(valid_float_params)

    def test_float_valid_zero(self):
        """Ноль — допустимое число."""
        checker = FloatFieldChecker("value", "Значение")
        params = {"value": 0.0}
        checker.check(params)

    def test_float_valid_negative(self):
        """Отрицательные числа допустимы, если не задан min_value."""
        checker = FloatFieldChecker("value", "Значение")
        params = {"value": -42.5}
        checker.check(params)

    def test_float_valid_scientific_notation(self):
        """Научная нотация допустима."""
        checker = FloatFieldChecker("value", "Значение")
        params = {"value": 1.5e-10}
        checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Обязательность
    # ------------------------------------------------------------------

    def test_float_required_missing(self):
        """Обязательное поле отсутствует -> ошибка."""
        checker = FloatFieldChecker("price", "Цена", required=True)
        params = {}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "Отсутствует обязательный параметр: 'price'" in str(exc.value)

    def test_float_required_with_none(self):
        """Обязательное поле с None -> ошибка."""
        checker = FloatFieldChecker("price", "Цена", required=True)
        params = {"price": None}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "Отсутствует обязательный параметр: 'price'" in str(exc.value)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Неверный тип
    # ------------------------------------------------------------------

    def test_float_wrong_type(self, wrong_type_float_params):
        """Неверный тип данных."""
        checker = FloatFieldChecker("price", "Цена")
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(wrong_type_float_params)
        assert "должно быть числом" in str(exc.value)

    def test_float_string_passed(self):
        """Передача строки вместо числа -> ошибка."""
        checker = FloatFieldChecker("price", "Цена")
        params = {"price": "99.99"}
        with pytest.raises(ValidationFieldException):
            checker.check(params)

    def test_float_none_passed(self):
        """Передача None -> ошибка для обязательного поля."""
        checker = FloatFieldChecker("price", "Цена", required=True)
        params = {"price": None}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "Отсутствует обязательный параметр" in str(exc.value)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Минимальное значение
    # ------------------------------------------------------------------

    def test_float_min_value(self):
        """Проверка минимального значения."""
        checker = FloatFieldChecker("price", "Цена", min_value=0.0)

        # Меньше минимума
        params = {"price": -1.5}
        with pytest.raises(ValidationFieldException):
            checker.check(params)

        # Равно минимуму
        params = {"price": 0.0}
        checker.check(params)

        # Больше минимума
        params = {"price": 10.5}
        checker.check(params)

    def test_float_min_value_negative(self):
        """Минимальное значение может быть отрицательным."""
        checker = FloatFieldChecker("temp", "Температура", min_value=-10.5)

        params = {"temp": -15.0}
        with pytest.raises(ValidationFieldException):
            checker.check(params)

        params = {"temp": -10.5}
        checker.check(params)

        params = {"temp": -5.0}
        checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Максимальное значение
    # ------------------------------------------------------------------

    def test_float_max_value(self):
        """Проверка максимального значения."""
        checker = FloatFieldChecker("price", "Цена", max_value=1000.0)

        # Больше максимума
        params = {"price": 1000.01}
        with pytest.raises(ValidationFieldException):
            checker.check(params)

        # Равно максимуму
        params = {"price": 1000.0}
        checker.check(params)

        # Меньше максимума
        params = {"price": 999.99}
        checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Диапазон значений
    # ------------------------------------------------------------------

    def test_float_range(self):
        """Проверка диапазона."""
        checker = FloatFieldChecker("temp", "Температура", min_value=-10.0, max_value=40.0)

        # Ниже минимума
        params = {"temp": -15.0}
        with pytest.raises(ValidationFieldException):
            checker.check(params)

        # В диапазоне
        params = {"temp": 20.5}
        checker.check(params)

        # Выше максимума
        params = {"temp": 45.0}
        with pytest.raises(ValidationFieldException):
            checker.check(params)

    def test_float_range_inclusive(self):
        """Границы диапазона включены."""
        checker = FloatFieldChecker("temp", "Температура", min_value=-10.0, max_value=40.0)

        # Минимальное значение
        params = {"temp": -10.0}
        checker.check(params)

        # Максимальное значение
        params = {"temp": 40.0}
        checker.check(params)

    def test_float_range_with_precision(self):
        """Проверка диапазона с плавающей точкой."""
        checker = FloatFieldChecker("value", "Значение", min_value=0.1, max_value=0.3)

        # Чуть ниже минимума
        params = {"value": 0.0999999}
        with pytest.raises(ValidationFieldException):
            checker.check(params)

        # Минимум
        params = {"value": 0.1}
        checker.check(params)

        # Максимум
        params = {"value": 0.3}
        checker.check(params)

        # Чуть выше максимума
        params = {"value": 0.3000001}
        with pytest.raises(ValidationFieldException):
            checker.check(params)
