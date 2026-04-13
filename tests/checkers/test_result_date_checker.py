# tests/checkers/test_result_date_checker.py
"""
Тесты ResultDateChecker — чекер полей с датой в результате аспекта.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что ResultDateChecker корректно валидирует поля с датами
в словаре результата аспекта. Принимает объекты datetime и строки,
разбираемые по указанному формату (date_format). Поддерживает
проверку диапазона (min_date, max_date).

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

TestValidValues
    - datetime-объект принимается без формата.
    - Строка, соответствующая date_format, принимается.
    - Дата на границе min_date / max_date принимается (включительно).
    - Дата внутри диапазона принимается.

TestInvalidValues
    - Целое число, список, словарь, bool — не datetime и не строка, ошибка.
    - Строка без указанного date_format — ошибка (формат обязателен).
    - Строка, не соответствующая формату — ошибка.
    - Дата меньше min_date — ошибка.
    - Дата больше max_date — ошибка.

TestRequired
    - required=True: отсутствующее или None поле — ошибка.
    - required=False: отсутствующее или None поле допускается.
    - required=False: присутствующее невалидное значение — ошибка.

TestDecorator
    - result_date записывает _checker_meta с корректными параметрами.
    - Параметры date_format, min_date, max_date попадают в extra_params.
    - Декоратор возвращает оригинальную функцию.
    - Несколько декораторов накапливаются.
"""

from datetime import UTC, datetime

import pytest

from action_machine.intents.checkers.result_date_checker import ResultDateChecker, result_date
from action_machine.model.exceptions import ValidationFieldError

# ═════════════════════════════════════════════════════════════════════════════
# Валидные значения
# ═════════════════════════════════════════════════════════════════════════════


class TestValidValues:
    """Проверяет, что корректные даты принимаются без ошибок."""

    def test_datetime_object_accepted(self):
        """Объект datetime принимается без указания формата."""
        # Arrange
        checker = ResultDateChecker("created_at", required=True)
        dt = datetime(2024, 6, 15, 12, 30, 0)

        # Act & Assert — исключения нет
        checker.check({"created_at": dt})

    def test_datetime_with_timezone_accepted(self):
        """Объект datetime с timezone принимается."""
        # Arrange
        checker = ResultDateChecker("created_at", required=True)
        dt = datetime(2024, 6, 15, 12, 30, 0, tzinfo=UTC)

        # Act & Assert — исключения нет
        checker.check({"created_at": dt})

    def test_string_with_format_accepted(self):
        """Строка, соответствующая date_format, принимается."""
        # Arrange
        checker = ResultDateChecker(
            "created_at",
            required=True,
            date_format="%Y-%m-%d",
        )

        # Act & Assert — исключения нет
        checker.check({"created_at": "2024-01-15"})

    def test_string_with_datetime_format_accepted(self):
        """Строка с форматом даты-времени принимается."""
        # Arrange
        checker = ResultDateChecker(
            "timestamp",
            required=True,
            date_format="%Y-%m-%d %H:%M:%S",
        )

        # Act & Assert — исключения нет
        checker.check({"timestamp": "2024-06-15 14:30:00"})

    def test_date_at_min_boundary_accepted(self):
        """Дата, равная min_date, принимается (включительно)."""
        # Arrange
        min_dt = datetime(2024, 1, 1)
        checker = ResultDateChecker(
            "event_date",
            required=True,
            min_date=min_dt,
        )

        # Act & Assert — исключения нет
        checker.check({"event_date": min_dt})

    def test_date_at_max_boundary_accepted(self):
        """Дата, равная max_date, принимается (включительно)."""
        # Arrange
        max_dt = datetime(2024, 12, 31)
        checker = ResultDateChecker(
            "event_date",
            required=True,
            max_date=max_dt,
        )

        # Act & Assert — исключения нет
        checker.check({"event_date": max_dt})

    def test_date_within_range_accepted(self):
        """Дата внутри диапазона min_date..max_date принимается."""
        # Arrange
        checker = ResultDateChecker(
            "event_date",
            required=True,
            min_date=datetime(2024, 1, 1),
            max_date=datetime(2024, 12, 31),
        )
        value = datetime(2024, 6, 15)

        # Act & Assert — исключения нет
        checker.check({"event_date": value})

    def test_string_date_within_range_accepted(self):
        """Строковая дата внутри диапазона принимается после парсинга."""
        # Arrange
        checker = ResultDateChecker(
            "event_date",
            required=True,
            date_format="%Y-%m-%d",
            min_date=datetime(2024, 1, 1),
            max_date=datetime(2024, 12, 31),
        )

        # Act & Assert — исключения нет
        checker.check({"event_date": "2024-06-15"})


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные значения
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidValues:
    """Проверяет отклонение невалидных значений с выбросом ValidationFieldError."""

    def test_int_rejected(self):
        """Целое число — не datetime и не строка."""
        # Arrange
        checker = ResultDateChecker("created_at", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"created_at": 20240115})

    def test_bool_rejected(self):
        """Bool — не datetime и не строка."""
        # Arrange
        checker = ResultDateChecker("created_at", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"created_at": True})

    def test_list_rejected(self):
        """Список — не datetime и не строка."""
        # Arrange
        checker = ResultDateChecker("created_at", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"created_at": [2024, 1, 15]})

    def test_dict_rejected(self):
        """Словарь — не datetime и не строка."""
        # Arrange
        checker = ResultDateChecker("created_at", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"created_at": {"year": 2024}})

    def test_string_without_format_raises(self):
        """Строка при отсутствии date_format вызывает ошибку."""
        # Arrange — date_format не задан
        checker = ResultDateChecker("created_at", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="формат"):
            checker.check({"created_at": "2024-01-15"})

    def test_string_wrong_format_raises(self):
        """Строка, не соответствующая date_format, вызывает ошибку."""
        # Arrange
        checker = ResultDateChecker(
            "created_at",
            required=True,
            date_format="%Y-%m-%d",
        )

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="формату"):
            checker.check({"created_at": "15/01/2024"})

    def test_date_below_min_raises(self):
        """Дата раньше min_date вызывает ошибку."""
        # Arrange
        checker = ResultDateChecker(
            "event_date",
            required=True,
            min_date=datetime(2024, 6, 1),
        )

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="не меньше"):
            checker.check({"event_date": datetime(2024, 5, 31)})

    def test_date_above_max_raises(self):
        """Дата позже max_date вызывает ошибку."""
        # Arrange
        checker = ResultDateChecker(
            "event_date",
            required=True,
            max_date=datetime(2024, 12, 31),
        )

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="не больше"):
            checker.check({"event_date": datetime(2025, 1, 1)})

    def test_string_date_below_min_raises(self):
        """Строковая дата раньше min_date вызывает ошибку после парсинга."""
        # Arrange
        checker = ResultDateChecker(
            "event_date",
            required=True,
            date_format="%Y-%m-%d",
            min_date=datetime(2024, 6, 1),
        )

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="не меньше"):
            checker.check({"event_date": "2024-05-01"})

    def test_string_date_above_max_raises(self):
        """Строковая дата позже max_date вызывает ошибку после парсинга."""
        # Arrange
        checker = ResultDateChecker(
            "event_date",
            required=True,
            date_format="%Y-%m-%d",
            max_date=datetime(2024, 12, 31),
        )

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="не больше"):
            checker.check({"event_date": "2025-01-01"})

    def test_error_message_contains_field_name(self):
        """Сообщение об ошибке содержит имя поля."""
        # Arrange
        checker = ResultDateChecker("delivery_date", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="delivery_date"):
            checker.check({"delivery_date": 12345})

    def test_error_message_contains_actual_type(self):
        """Сообщение об ошибке содержит фактический тип значения."""
        # Arrange
        checker = ResultDateChecker("delivery_date", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="int"):
            checker.check({"delivery_date": 12345})


# ═════════════════════════════════════════════════════════════════════════════
# Обязательность поля (required)
# ═════════════════════════════════════════════════════════════════════════════


class TestRequired:
    """Проверяет поведение флага required для обязательных и опциональных полей."""

    def test_required_missing_field_raises(self):
        """Отсутствующее обязательное поле вызывает ошибку."""
        # Arrange
        checker = ResultDateChecker("created_at", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({})

    def test_required_none_raises(self):
        """None в обязательном поле вызывает ошибку."""
        # Arrange
        checker = ResultDateChecker("created_at", required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"created_at": None})

    def test_optional_missing_field_passes(self):
        """Отсутствующее опциональное поле допускается."""
        # Arrange
        checker = ResultDateChecker("created_at", required=False)

        # Act & Assert — исключения нет
        checker.check({})

    def test_optional_none_passes(self):
        """None в опциональном поле допускается."""
        # Arrange
        checker = ResultDateChecker("created_at", required=False)

        # Act & Assert — исключения нет
        checker.check({"created_at": None})

    def test_optional_invalid_type_still_raises(self):
        """Даже в опциональном поле невалидный тип вызывает ошибку."""
        # Arrange
        checker = ResultDateChecker("created_at", required=False)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"created_at": 12345})


# ═════════════════════════════════════════════════════════════════════════════
# Дополнительные параметры (_get_extra_params)
# ═════════════════════════════════════════════════════════════════════════════


class TestExtraParams:
    """Проверяет, что _get_extra_params возвращает корректные параметры."""

    def test_extra_params_all_none_by_default(self):
        """Без дополнительных параметров все значения None."""
        # Arrange
        checker = ResultDateChecker("created_at")

        # Act
        params = checker._get_extra_params()

        # Assert
        assert params["date_format"] is None
        assert params["min_date"] is None
        assert params["max_date"] is None

    def test_extra_params_with_format(self):
        """date_format сохраняется в extra_params."""
        # Arrange
        checker = ResultDateChecker("created_at", date_format="%Y-%m-%d")

        # Act
        params = checker._get_extra_params()

        # Assert
        assert params["date_format"] == "%Y-%m-%d"

    def test_extra_params_with_range(self):
        """min_date и max_date сохраняются в extra_params."""
        # Arrange
        min_dt = datetime(2024, 1, 1)
        max_dt = datetime(2024, 12, 31)
        checker = ResultDateChecker(
            "event_date",
            min_date=min_dt,
            max_date=max_dt,
        )

        # Act
        params = checker._get_extra_params()

        # Assert
        assert params["min_date"] == min_dt
        assert params["max_date"] == max_dt


# ═════════════════════════════════════════════════════════════════════════════
# Декоратор result_date
# ═════════════════════════════════════════════════════════════════════════════


class TestDecorator:
    """Проверяет, что декоратор result_date записывает метаданные в функцию."""

    def test_checker_meta_attached(self):
        """Декоратор создаёт атрибут _checker_meta."""
        # Arrange & Act
        @result_date("created_at", date_format="%Y-%m-%d")
        async def aspect(self, params, state, box, connections):
            return {"created_at": "2024-01-15"}

        # Assert
        assert hasattr(aspect, "_checker_meta")
        assert len(aspect._checker_meta) == 1

    def test_checker_class_is_result_date_checker(self):
        """Метаданные содержат правильный класс чекера."""
        # Arrange & Act
        @result_date("created_at")
        async def aspect(self, params, state, box, connections):
            return {"created_at": datetime(2024, 1, 15)}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["checker_class"] is ResultDateChecker

    def test_field_name_recorded(self):
        """Имя поля сохраняется в метаданных."""
        # Arrange & Act
        @result_date("delivery_date")
        async def aspect(self, params, state, box, connections):
            return {"delivery_date": datetime(2024, 6, 15)}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["field_name"] == "delivery_date"

    def test_required_default_true(self):
        """По умолчанию required=True."""
        # Arrange & Act
        @result_date("created_at")
        async def aspect(self, params, state, box, connections):
            return {"created_at": datetime(2024, 1, 15)}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["required"] is True

    def test_required_false_recorded(self):
        """Явное required=False сохраняется."""
        # Arrange & Act
        @result_date("created_at", required=False)
        async def aspect(self, params, state, box, connections):
            return {"created_at": None}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["required"] is False

    def test_extra_params_in_meta(self):
        """date_format, min_date, max_date доступны через экземпляр чекера."""
        # Arrange
        min_dt = datetime(2024, 1, 1)
        max_dt = datetime(2024, 12, 31)

        # Act
        @result_date(
            "event_date",
            date_format="%Y-%m-%d",
            min_date=min_dt,
            max_date=max_dt,
        )
        async def aspect(self, params, state, box, connections):
            return {"event_date": "2024-06-15"}

        # Assert — проверяем, что метаданные записаны и чекер работает корректно
        meta = aspect._checker_meta[0]
        assert meta["checker_class"] is ResultDateChecker
        assert meta["field_name"] == "event_date"
        # Дополнительные параметры проверяем через сам чекер
        checker = ResultDateChecker(
            "event_date",
            date_format="%Y-%m-%d",
            min_date=min_dt,
            max_date=max_dt,
        )
        extra = checker._get_extra_params()
        assert extra["date_format"] == "%Y-%m-%d"
        assert extra["min_date"] == min_dt
        assert extra["max_date"] == max_dt

    def test_decorator_returns_original_function(self):
        """Декоратор возвращает оригинальную функцию без изменений."""
        # Arrange
        async def original(self, params, state, box, connections):
            return {"created_at": datetime(2024, 1, 15)}

        # Act
        decorated = result_date("created_at")(original)

        # Assert
        assert decorated is original

    def test_multiple_decorators_accumulate(self):
        """Несколько декораторов на одном методе создают список метаданных."""
        # Arrange & Act
        @result_date("created_at", date_format="%Y-%m-%d")
        @result_date("updated_at", date_format="%Y-%m-%d %H:%M:%S")
        async def aspect(self, params, state, box, connections):
            return {
                "created_at": "2024-01-15",
                "updated_at": "2024-06-15 14:30:00",
            }

        # Assert
        assert len(aspect._checker_meta) == 2
        field_names = {m["field_name"] for m in aspect._checker_meta}
        assert field_names == {"created_at", "updated_at"}
