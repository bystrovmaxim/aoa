# tests/checkers/test_base_checker.py
"""
Тесты для BaseFieldChecker — базового класса всех чекеров.

Проверяем:
- Использование чекера как декоратора класса (добавление в _field_checkers)
- Использование чекера как декоратора метода (_result_checkers)
- Ошибка при применении к не-классу и не-callable
- Проверка обязательности поля
- Установка имени поля в исключении, если его нет
"""

from typing import Any

import pytest

from action_machine.Checkers.BaseFieldChecker import BaseFieldChecker
from action_machine.Core.Exceptions import ValidationFieldError

# ----------------------------------------------------------------------
# Тестовый чекер (конкретная реализация)
# ----------------------------------------------------------------------

class MockChecker(BaseFieldChecker):
    """Чекер для тестов, всегда успешный."""

    def __init__(self, field_name: str, desc: str = "", required: bool = True):
        super().__init__(field_name, required, desc)

    def _check_type_and_constraints(self, value: Any) -> None:
        # Всегда успех
        pass


# ----------------------------------------------------------------------
# Тестовые классы и функции
# ----------------------------------------------------------------------

class TargetClass:
    pass


def target_func():
    pass


# ======================================================================
# ТЕСТЫ
# ======================================================================

class TestBaseFieldChecker:
    """Тесты для BaseFieldChecker."""

    # ------------------------------------------------------------------
    # Тесты декоратора
    # ------------------------------------------------------------------

    def test_checker_as_class_decorator(self):
        """Применение к классу добавляет чекер в _field_checkers."""
        checker = MockChecker("field1")

        @checker
        class MyClass:
            pass

        assert hasattr(MyClass, "_field_checkers")
        assert len(MyClass._field_checkers) == 1
        assert MyClass._field_checkers[0] is checker

    def test_checker_as_method_decorator(self):
        """Применение к методу добавляет чекер в _result_checkers метода."""
        checker = MockChecker("field1")

        class MyClass:
            @checker
            def my_method(self):
                pass

        assert hasattr(MyClass.my_method, "_result_checkers")
        assert len(MyClass.my_method._result_checkers) == 1
        assert MyClass.my_method._result_checkers[0] is checker

    def test_checker_on_non_class_non_callable_raises_type_error(self):
        """Применение к объекту, не являющемуся классом или callable, вызывает TypeError."""
        checker = MockChecker("field1")
        obj = 42

        with pytest.raises(TypeError, match="может применяться только к классам или методам"):
            checker(obj)

    # ------------------------------------------------------------------
    # Тесты check()
    # ------------------------------------------------------------------

    def test_check_required_field_missing_raises(self):
        """Обязательное поле отсутствует → ValidationFieldError."""
        checker = MockChecker("name", required=True)
        params = {}

        with pytest.raises(ValidationFieldError) as exc:
            checker.check(params)
        assert "Отсутствует обязательный параметр: 'name'" in str(exc.value)
        assert exc.value.field == "name"

    def test_check_not_required_field_missing_passes(self):
        """Необязательное поле отсутствует — проверка проходит без ошибок."""
        checker = MockChecker("name", required=False)
        params = {}

        # Не должно быть исключения
        checker.check(params)

    def test_check_sets_field_name_on_exception_without_field(self):
        """Если _check_type_and_constraints кидает исключение без field, check устанавливает field."""

        class ThrowingChecker(BaseFieldChecker):
            def __init__(self, field_name):
                super().__init__(field_name, required=True, desc="")

            def _check_type_and_constraints(self, value):
                raise ValidationFieldError("Ошибка")  # без field

        checker = ThrowingChecker("test")
        params = {"test": 42}

        with pytest.raises(ValidationFieldError) as exc:
            checker.check(params)
        assert exc.value.field == "test"