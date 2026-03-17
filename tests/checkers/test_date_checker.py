"""
Тесты для DateFieldChecker.

Проверяем:
- Валидные объекты datetime
- Валидные строки с форматом
- Отсутствие формата для строк
- Неверный формат строки
- Диапазоны дат (min, max)
- Неверные типы данных
"""

from datetime import datetime

import pytest

from action_machine.Checkers.DateFieldChecker import DateFieldChecker
from action_machine.Core.Exceptions import ValidationFieldError


class TestDateFieldChecker:
    """Тесты для чекера дат."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Валидные значения
    # ------------------------------------------------------------------

    def test_date_valid_datetime(self, valid_date_params):
        """Объект datetime проходит."""
        checker = DateFieldChecker("created", "Дата создания")
        checker.check(valid_date_params)

    def test_date_valid_string(self):
        """Строка с датой проходит при указанном формате."""
        checker = DateFieldChecker("created", "Дата создания", format="%Y-%m-%d")
        params = {"created": "2024-01-01"}
        checker.check(params)

    def test_date_valid_string_with_time(self):
        """Строка с датой и временем."""
        checker = DateFieldChecker("created", "Дата создания", format="%Y-%m-%d %H:%M:%S")
        params = {"created": "2024-01-01 15:30:00"}
        checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Обязательность
    # ------------------------------------------------------------------

    def test_date_required_missing(self):
        """Обязательное поле отсутствует -> ошибка."""
        checker = DateFieldChecker("created", "Дата создания", required=True)
        params = {}
        with pytest.raises(ValidationFieldError) as exc:
            checker.check(params)
        assert "Отсутствует обязательный параметр: 'created'" in str(exc.value)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Формат строки
    # ------------------------------------------------------------------

    def test_date_string_without_format(self):
        """Строка без указания формата -> ошибка."""
        checker = DateFieldChecker("created", "Дата создания")
        params = {"created": "2024-01-01"}
        with pytest.raises(ValidationFieldError) as exc:
            checker.check(params)
        assert "требуется указать формат даты" in str(exc.value)

    def test_date_string_wrong_format(self):
        """Строка не соответствует формату -> ошибка."""
        checker = DateFieldChecker("created", "Дата создания", format="%Y-%m-%d")
        params = {"created": "01-01-2024"}
        with pytest.raises(ValidationFieldError) as exc:
            checker.check(params)
        assert "должно быть строкой даты, соответствующей формату" in str(exc.value)

    def test_date_string_invalid_date(self):
        """Строка с несуществующей датой -> ошибка."""
        checker = DateFieldChecker("created", "Дата создания", format="%Y-%m-%d")
        params = {"created": "2024-13-45"}  # невалидная дата
        with pytest.raises(ValidationFieldError):
            checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Неверный тип
    # ------------------------------------------------------------------

    def test_date_wrong_type(self, wrong_type_date_params):
        """Неверный тип данных."""
        checker = DateFieldChecker("created", "Дата создания")
        with pytest.raises(ValidationFieldError):
            checker.check(wrong_type_date_params)

    def test_date_int_passed(self):
        """int вместо даты -> ошибка."""
        checker = DateFieldChecker("created", "Дата создания")
        params = {"created": 20240101}
        with pytest.raises(ValidationFieldError):
            checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Минимальная дата
    # ------------------------------------------------------------------

    def test_date_min_date(self):
        """Проверка минимальной даты."""
        min_date = datetime(2024, 1, 1)
        checker = DateFieldChecker("created", "Дата создания", min_date=min_date)

        # Дата раньше минимума
        params = {"created": datetime(2023, 12, 31)}
        with pytest.raises(ValidationFieldError) as exc:
            checker.check(params)
        assert "должно быть не меньше" in str(exc.value)

        # Равно минимуму
        params = {"created": datetime(2024, 1, 1)}
        checker.check(params)

        # Позже минимума
        params = {"created": datetime(2024, 6, 1)}
        checker.check(params)

    def test_date_min_date_with_string(self):
        """Минимальная дата со строковым вводом."""
        min_date = datetime(2024, 1, 1)
        checker = DateFieldChecker("created", "Дата создания", format="%Y-%m-%d", min_date=min_date)

        params = {"created": "2023-12-31"}
        with pytest.raises(ValidationFieldError):
            checker.check(params)

        params = {"created": "2024-01-01"}
        checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Максимальная дата
    # ------------------------------------------------------------------

    def test_date_max_date(self):
        """Проверка максимальной даты."""
        max_date = datetime(2024, 12, 31)
        checker = DateFieldChecker("created", "Дата создания", max_date=max_date)

        # Дата позже максимума
        params = {"created": datetime(2025, 1, 1)}
        with pytest.raises(ValidationFieldError) as exc:
            checker.check(params)
        assert "должно быть не больше" in str(exc.value)

        # Равно максимуму
        params = {"created": datetime(2024, 12, 31)}
        checker.check(params)

        # Раньше максимума
        params = {"created": datetime(2024, 6, 1)}
        checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Диапазон дат
    # ------------------------------------------------------------------

    def test_date_range(self):
        """Проверка диапазона дат."""
        min_date = datetime(2024, 1, 1)
        max_date = datetime(2024, 12, 31)
        checker = DateFieldChecker("created", "Дата создания", min_date=min_date, max_date=max_date)

        # Ниже минимума
        params = {"created": datetime(2023, 12, 31)}
        with pytest.raises(ValidationFieldError):
            checker.check(params)

        # В диапазоне
        params = {"created": datetime(2024, 6, 1)}
        checker.check(params)

        # Выше максимума
        params = {"created": datetime(2025, 1, 1)}
        with pytest.raises(ValidationFieldError):
            checker.check(params)

    def test_date_range_with_string(self):
        """Диапазон дат со строковым вводом."""
        min_date = datetime(2024, 1, 1)
        max_date = datetime(2024, 12, 31)
        checker = DateFieldChecker("created", "Дата создания", format="%Y-%m-%d", min_date=min_date, max_date=max_date)

        params = {"created": "2023-12-31"}
        with pytest.raises(ValidationFieldError):
            checker.check(params)

        params = {"created": "2024-06-15"}
        checker.check(params)

        params = {"created": "2025-01-01"}
        with pytest.raises(ValidationFieldError):
            checker.check(params)

    def test_date_range_inclusive(self):
        """Границы диапазона включены."""
        min_date = datetime(2024, 1, 1)
        max_date = datetime(2024, 12, 31)
        checker = DateFieldChecker("created", "Дата создания", min_date=min_date, max_date=max_date)

        # Минимум
        params = {"created": datetime(2024, 1, 1)}
        checker.check(params)

        # Максимум
        params = {"created": datetime(2024, 12, 31)}
        checker.check(params)
