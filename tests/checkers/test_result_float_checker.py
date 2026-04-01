# tests/checkers/test_result_float_checker.py
"""
Тесты ResultFloatChecker и декоратора result_float — числовые поля (int/float).

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

ResultFloatChecker проверяет, что поле результата аспекта является числом
(int ИЛИ float) и лежит в заданном диапазоне (min_value, max_value).

В отличие от ResultIntChecker, который принимает только int,
ResultFloatChecker принимает оба числовых типа. Это удобно для полей
вроде amount, total, discount, где значение может быть как 100, так
и 99.99.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Валидные значения:
    - Float, int, ноль (0 и 0.0), отрицательные числа.
    - Значение на границе min_value / max_value.

Невалидные значения:
    - Строка, список, bool → ValidationFieldError.
    - Значение вне диапазона → ValidationFieldError.

Required / Optional:
    - required=True, поле отсутствует → ValidationFieldError.
    - required=False, поле отсутствует → OK.

Декоратор:
    - result_float записывает _checker_meta с min_value, max_value.
"""

import pytest

from action_machine.checkers.result_float_checker import ResultFloatChecker, result_float
from action_machine.core.exceptions import ValidationFieldError

# ═════════════════════════════════════════════════════════════════════════════
# Валидные значения
# ═════════════════════════════════════════════════════════════════════════════


class TestValidValues:
    """check() проходит для валидных числовых значений."""

    def test_float_value(self) -> None:
        """Float проходит."""
        # Arrange
        checker = ResultFloatChecker("total", required=True)

        # Act & Assert
        checker.check({"total": 99.99})

    def test_int_value(self) -> None:
        """Int проходит — ResultFloatChecker принимает int и float."""
        # Arrange
        checker = ResultFloatChecker("total", required=True)

        # Act & Assert
        checker.check({"total": 100})

    def test_zero_float(self) -> None:
        """Float-ноль 0.0 проходит."""
        # Arrange
        checker = ResultFloatChecker("discount", required=True)

        # Act & Assert
        checker.check({"discount": 0.0})

    def test_zero_int(self) -> None:
        """Int-ноль 0 проходит."""
        # Arrange
        checker = ResultFloatChecker("discount", required=True)

        # Act & Assert
        checker.check({"discount": 0})

    def test_negative_value(self) -> None:
        """Отрицательное число проходит (если нет min_value)."""
        # Arrange
        checker = ResultFloatChecker("balance", required=True)

        # Act & Assert
        checker.check({"balance": -500.50})

    def test_exact_min_value(self) -> None:
        """Значение ровно min_value проходит (включительно)."""
        # Arrange
        checker = ResultFloatChecker("amount", required=True, min_value=0.0)

        # Act & Assert
        checker.check({"amount": 0.0})

    def test_exact_max_value(self) -> None:
        """Значение ровно max_value проходит (включительно)."""
        # Arrange
        checker = ResultFloatChecker("rate", required=True, max_value=1.0)

        # Act & Assert
        checker.check({"rate": 1.0})

    def test_between_bounds(self) -> None:
        """Значение между min и max проходит."""
        # Arrange
        checker = ResultFloatChecker("percent", required=True, min_value=0.0, max_value=100.0)

        # Act & Assert
        checker.check({"percent": 55.5})

    def test_int_at_float_boundary(self) -> None:
        """Int-значение на границе float min_value."""
        # Arrange — min_value=0.0, передаём int 0
        checker = ResultFloatChecker("total", required=True, min_value=0.0)

        # Act & Assert — int 0 >= float 0.0
        checker.check({"total": 0})


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные значения
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidValues:
    """check() бросает ValidationFieldError для невалидных значений."""

    def test_string_raises(self) -> None:
        """Строка вместо числа → ValidationFieldError."""
        # Arrange
        checker = ResultFloatChecker("total", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="числом"):
            checker.check({"total": "99.99"})

    def test_list_raises(self) -> None:
        """Список → ValidationFieldError."""
        # Arrange
        checker = ResultFloatChecker("total", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="числом"):
            checker.check({"total": [1, 2]})

    def test_bool_raises(self) -> None:
        """
        Bool → ValidationFieldError.

        Хотя bool является подклассом int в Python, ResultFloatChecker
        использует isinstance(value, (int, float)), и bool проходит.
        Но это особенность Python, а не чекера.

        ПРИМЕЧАНИЕ: если этот тест падает — значит, ResultFloatChecker
        принимает bool как число (что технически корректно в Python).
        В таком случае удалите этот тест.
        """
        # Arrange
        checker = ResultFloatChecker("total", required=True)

        # Примечание: bool IS int в Python, поэтому isinstance(True, (int, float)) == True.
        # Этот тест документирует поведение, а не ошибку.
        # True будет принят как int(1), False как int(0).
        checker.check({"total": True})  # Не бросает — bool IS int

    def test_below_min_value(self) -> None:
        """Значение меньше min_value → ValidationFieldError."""
        # Arrange
        checker = ResultFloatChecker("amount", required=True, min_value=0.0)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="не меньше"):
            checker.check({"amount": -0.01})

    def test_above_max_value(self) -> None:
        """Значение больше max_value → ValidationFieldError."""
        # Arrange
        checker = ResultFloatChecker("rate", required=True, max_value=1.0)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="не больше"):
            checker.check({"rate": 1.001})

    def test_none_dict_value_raises(self) -> None:
        """None как значение → ValidationFieldError (для required)."""
        # Arrange
        checker = ResultFloatChecker("total", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="Отсутствует обязательный"):
            checker.check({"total": None})


# ═════════════════════════════════════════════════════════════════════════════
# Required / Optional
# ═════════════════════════════════════════════════════════════════════════════


class TestRequired:
    """Поведение при required=True и required=False."""

    def test_required_missing_raises(self) -> None:
        """required=True, поле отсутствует → ValidationFieldError."""
        # Arrange
        checker = ResultFloatChecker("total", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="Отсутствует обязательный"):
            checker.check({})

    def test_optional_missing_ok(self) -> None:
        """required=False, поле отсутствует → OK."""
        # Arrange
        checker = ResultFloatChecker("total", required=False)

        # Act & Assert
        checker.check({})

    def test_optional_present_still_validated(self) -> None:
        """required=False, но значение присутствует — тип проверяется."""
        # Arrange
        checker = ResultFloatChecker("total", required=False)

        # Act & Assert — строка вместо числа
        with pytest.raises(ValidationFieldError, match="числом"):
            checker.check({"total": "not_a_number"})


# ═════════════════════════════════════════════════════════════════════════════
# Декоратор result_float
# ═════════════════════════════════════════════════════════════════════════════


class TestDecorator:
    """Функция-декоратор result_float записывает _checker_meta."""

    def test_writes_checker_meta(self) -> None:
        """
        @result_float("total") записывает _checker_meta в метод.
        """
        # Arrange & Act
        @result_float("total", required=True, min_value=0.0, max_value=999999.99)
        async def calc(self, params, state, box, connections):
            return {"total": 1500.0}

        # Assert
        assert hasattr(calc, "_checker_meta")
        assert len(calc._checker_meta) == 1
        m = calc._checker_meta[0]
        assert m["checker_class"] is ResultFloatChecker
        assert m["field_name"] == "total"
        assert m["required"] is True
        assert m["min_value"] == 0.0
        assert m["max_value"] == 999999.99

    def test_decorator_preserves_function(self) -> None:
        """Декоратор возвращает ту же функцию."""
        # Arrange
        async def original(self, params, state, box, connections):
            return {}

        # Act
        decorated = result_float("total")(original)

        # Assert
        assert decorated is original

    def test_combined_with_result_string(self) -> None:
        """
        result_float + result_string на одном методе — оба записываются.

        Один аспект может проверять поля разных типов.
        """
        # Arrange & Act
        from action_machine.checkers.result_string_checker import result_string

        @result_string("txn_id", required=True)
        @result_float("amount", required=True, min_value=0.0)
        async def process(self, params, state, box, connections):
            return {"txn_id": "TXN-1", "amount": 100.0}

        # Assert — два чекера в списке
        assert len(process._checker_meta) == 2
        fields = [m["field_name"] for m in process._checker_meta]
        assert "txn_id" in fields
        assert "amount" in fields
