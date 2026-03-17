"""
Тесты для StringFieldChecker.

Проверяем:
- Валидные строки
- Обязательные и необязательные поля
- Ограничения по длине (min, max)
- Проверка на пустую строку
- Неверные типы данных
"""

import pytest

from action_machine.Checkers.StringFieldChecker import StringFieldChecker
from action_machine.Core.Exceptions import ValidationFieldException


class TestStringFieldChecker:
    """Тесты для строкового чекера."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Валидные значения
    # ------------------------------------------------------------------

    def test_string_valid(self, valid_string_params):
        """Корректная строка проходит проверку."""
        checker = StringFieldChecker("name", "Имя пользователя")
        checker.check(valid_string_params)  # не должно быть исключения

    def test_string_valid_with_all_constraints(self):
        """Все ограничения одновременно с валидным значением."""
        checker = StringFieldChecker("name", "Имя", required=True, min_length=3, max_length=10, not_empty=True)
        params = {"name": "John"}
        checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Обязательность
    # ------------------------------------------------------------------

    def test_string_required_missing(self):
        """Обязательное поле отсутствует -> ошибка."""
        checker = StringFieldChecker("name", "Имя пользователя", required=True)
        params = {}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "Отсутствует обязательный параметр: 'name'" in str(exc.value)
        assert exc.value.field == "name"

    def test_string_required_with_none(self):
        """
        Обязательное поле с None -> ошибка.
        None считается отсутствием значения.
        """
        checker = StringFieldChecker("name", "Имя", required=True)
        params = {"name": None}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "Отсутствует обязательный параметр: 'name'" in str(exc.value)

    def test_string_not_required_with_none(self):
        """
        Необязательное поле с None -> проверка типа.
        None не является строкой, поэтому должна быть ошибка типа.
        """
        checker = StringFieldChecker("name", "Имя", required=False)
        params = {"name": None}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "должен быть строкой" in str(exc.value)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Неверный тип
    # ------------------------------------------------------------------

    def test_string_wrong_type(self, wrong_type_string_params):
        """Неверный тип данных."""
        checker = StringFieldChecker("name", "Имя пользователя")
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(wrong_type_string_params)
        assert "должен быть строкой" in str(exc.value)
        assert exc.value.field == "name"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Ограничения по длине
    # ------------------------------------------------------------------

    def test_string_min_length(self):
        """Проверка минимальной длины."""
        checker = StringFieldChecker("name", "Имя", min_length=3)

        # Слишком короткое
        params = {"name": "Jo"}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "Длина параметра 'name' должна быть не меньше 3" in str(exc.value)

        # Нормальная длина
        params = {"name": "John"}
        checker.check(params)

    def test_string_max_length(self):
        """Проверка максимальной длины."""
        checker = StringFieldChecker("name", "Имя", max_length=5)

        # Слишком длинное
        params = {"name": "Jonathan"}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "Длина параметра 'name' должна быть не больше 5" in str(exc.value)

        # Нормальная длина
        params = {"name": "John"}
        checker.check(params)

    def test_string_min_max_length(self):
        """Проверка диапазона длины."""
        checker = StringFieldChecker("name", "Имя", min_length=3, max_length=10)

        # Слишком короткое
        params = {"name": "Jo"}
        with pytest.raises(ValidationFieldException):
            checker.check(params)

        # Нормальное
        params = {"name": "John"}
        checker.check(params)

        # Слишком длинное
        params = {"name": "Johnathan John"}
        with pytest.raises(ValidationFieldException):
            checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Пустые строки
    # ------------------------------------------------------------------

    def test_string_not_empty(self):
        """Проверка на непустую строку."""
        checker = StringFieldChecker("name", "Имя", not_empty=True)

        # Пустая строка
        params = {"name": ""}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "не может быть пустым" in str(exc.value)

        # Непустая строка
        params = {"name": "John"}
        checker.check(params)

    def test_string_not_empty_with_spaces_only(self):
        """Строка из пробелов не считается пустой, если not_empty=True."""
        checker = StringFieldChecker("name", "Имя", not_empty=True)
        params = {"name": "   "}
        # Строка из пробелов не пустая (len > 0)
        checker.check(params)

    def test_string_not_empty_with_min_length(self):
        """Комбинация not_empty и min_length."""
        checker = StringFieldChecker("name", "Имя", not_empty=True, min_length=3)

        # Пустая строка -> not_empty
        params = {"name": ""}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "не может быть пустым" in str(exc.value)

        # Слишком короткая -> min_length
        params = {"name": "ab"}
        with pytest.raises(ValidationFieldException) as exc:
            checker.check(params)
        assert "должна быть не меньше 3" in str(exc.value)

        # Нормальная
        params = {"name": "abc"}
        checker.check(params)
