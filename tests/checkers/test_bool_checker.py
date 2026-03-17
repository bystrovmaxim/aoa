"""
Тесты для BoolFieldChecker.

Проверяем:
- Валидные булевы значения (True, False)
- Обязательные и необязательные поля
- Неверные типы (int, string, list, dict)
- None как отдельный случай
"""

import pytest

from action_machine.Checkers.BoolFieldChecker import BoolFieldChecker
from action_machine.Core.Exceptions import ValidationFieldException


class TestBoolFieldChecker:
    """Тесты для булева чекера."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Валидные значения
    # ------------------------------------------------------------------

    def test_bool_valid_true(self):
        """True проходит."""
        checker = BoolFieldChecker("active", "Активен")
        params = {"active": True}
        checker.check(params)

    def test_bool_valid_false(self):
        """False проходит."""
        checker = BoolFieldChecker("active", "Активен")
        params = {"active": False}
        checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Обязательность
    # ------------------------------------------------------------------

    def test_bool_required_missing(self):
        """Обязательное поле отсутствует -> ошибка."""
        checker = BoolFieldChecker("active", "Активен", required=True)
        params = {}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "Отсутствует обязательный параметр: 'active'" in str(exc.value)

    def test_bool_required_with_none(self):
        """
        Обязательное поле с None -> ошибка.
        None считается отсутствием значения.
        """
        checker = BoolFieldChecker("active", "Активен", required=True)
        params = {"active": None}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "Отсутствует обязательный параметр: 'active'" in str(exc.value)

    def test_bool_not_required_with_none(self):
        """
        Необязательное поле с None -> проверка типа.
        None не является bool, поэтому ошибка.
        """
        checker = BoolFieldChecker("active", "Активен", required=False)
        params = {"active": None}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "должен быть булевым" in str(exc.value)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Неверный тип (значения присутствуют)
    # ------------------------------------------------------------------

    def test_bool_wrong_type_int(self):
        """int вместо bool -> ошибка."""
        checker = BoolFieldChecker("active", "Активен", required=True)

        wrong_values = [1, 0, -1, 42]
        for val in wrong_values:
            params = {"active": val}
            with pytest.raises(ValidationFieldException) as exc:
                checker.check(params)
            assert "должен быть булевым" in str(exc.value)

    def test_bool_wrong_type_string(self):
        """string вместо bool -> ошибка."""
        checker = BoolFieldChecker("active", "Активен")

        wrong_values = ["true", "false", "yes", "no", "True", "False", ""]
        for val in wrong_values:
            params = {"active": val}
            with pytest.raises(ValidationFieldException) as exc:
                checker.check(params)
            assert "должен быть булевым" in str(exc.value)

    def test_bool_wrong_type_list(self):
        """list вместо bool -> ошибка."""
        checker = BoolFieldChecker("active", "Активен")

        wrong_values = [[], [1, 2, 3], ["a"]]
        for val in wrong_values:
            params = {"active": val}
            with pytest.raises(ValidationFieldException) as exc:
                checker.check(params)
            assert "должен быть булевым" in str(exc.value)

    def test_bool_wrong_type_dict(self):
        """dict вместо bool -> ошибка."""
        checker = BoolFieldChecker("active", "Активен")

        wrong_values = [{}, {"key": "value"}]
        for val in wrong_values:
            params = {"active": val}
            with pytest.raises(ValidationFieldException) as exc:
                checker.check(params)
            assert "должен быть булевым" in str(exc.value)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Комбинации с required
    # ------------------------------------------------------------------

    def test_bool_required_with_wrong_type(self):
        """
        Обязательное поле с неверным типом -> ошибка типа,
        а не ошибка обязательности.
        """
        checker = BoolFieldChecker("active", "Активен", required=True)
        params = {"active": 123}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "должен быть булевым" in str(exc.value)
        assert "Отсутствует" not in str(exc.value)

    def test_bool_not_required_with_wrong_type(self):
        """Необязательное поле с неверным типом -> ошибка типа."""
        checker = BoolFieldChecker("active", "Активен", required=False)
        params = {"active": "true"}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "должен быть булевым" in str(exc.value)
