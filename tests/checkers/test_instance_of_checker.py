"""
Тесты для InstanceOfChecker.

Проверяем:
- Принадлежность одному классу
- Принадлежность нескольким классам (tuple)
- Пользовательские классы
- Обязательные поля
- Неверные типы
"""

import pytest

from action_machine.Checkers.InstanceOfChecker import InstanceOfChecker
from action_machine.Core.Exceptions import ValidationFieldError

from .conftest import Admin, User


class TestInstanceOfChecker:
    """Тесты для чекера проверки типа."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Один класс
    # ------------------------------------------------------------------

    def test_instanceof_single_class(self):
        """Проверка принадлежности одному классу."""
        checker = InstanceOfChecker("obj", str, "Строковый объект")

        # Валидное значение
        params = {"obj": "hello"}
        checker.check(params)

        # Невалидное значение
        params = {"obj": 123}
        with pytest.raises(ValidationFieldError) as exc:
            checker.check(params)
        assert "должно быть экземпляром класса str" in str(exc.value)

    def test_instanceof_single_class_with_int(self):
        """Проверка с int."""
        checker = InstanceOfChecker("num", int, "Целое число")

        params = {"num": 42}
        checker.check(params)

        params = {"num": "42"}
        with pytest.raises(ValidationFieldError) as exc:
            checker.check(params)
        assert "должно быть экземпляром класса int" in str(exc.value)

    def test_instanceof_single_class_with_float(self):
        """Проверка с float."""
        checker = InstanceOfChecker("num", float, "Число с плавающей точкой")

        params = {"num": 3.14}
        checker.check(params)

        params = {"num": 42}  # int не подходит
        with pytest.raises(ValidationFieldError):
            checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Несколько классов (tuple)
    # ------------------------------------------------------------------

    def test_instanceof_tuple_classes(self):
        """Проверка принадлежности нескольким классам."""
        checker = InstanceOfChecker("obj", (int, float), "Число")

        # int подходит
        params = {"obj": 42}
        checker.check(params)

        # float подходит
        params = {"obj": 3.14}
        checker.check(params)

        # str не подходит
        params = {"obj": "42"}
        with pytest.raises(ValidationFieldError) as exc:
            checker.check(params)
        assert "должно быть экземпляром одного из классов: int, float" in str(exc.value)

    def test_instanceof_tuple_with_mixed_classes(self):
        """Кортеж с разными классами."""
        checker = InstanceOfChecker("obj", (str, list, dict), "Строка, список или словарь")

        params = {"obj": "text"}
        checker.check(params)

        params = {"obj": [1, 2, 3]}
        checker.check(params)

        params = {"obj": {"key": "value"}}
        checker.check(params)

        params = {"obj": 42}
        with pytest.raises(ValidationFieldError):
            checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Пользовательские классы
    # ------------------------------------------------------------------

    def test_instanceof_custom_class(self):
        """Проверка с пользовательским классом."""
        checker = InstanceOfChecker("user", User, "Пользователь")

        params = {"user": User()}
        checker.check(params)

        params = {"user": Admin()}
        with pytest.raises(ValidationFieldError):
            checker.check(params)

    def test_instanceof_custom_classes_tuple(self):
        """Проверка с несколькими пользовательскими классами."""
        checker = InstanceOfChecker("user", (User, Admin), "Пользователь или админ")

        params = {"user": User()}
        checker.check(params)

        params = {"user": Admin()}
        checker.check(params)

        params = {"user": "not a user"}
        with pytest.raises(ValidationFieldError):
            checker.check(params)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Обязательность
    # ------------------------------------------------------------------

    def test_instanceof_required_missing(self):
        """Обязательное поле отсутствует -> ошибка."""
        checker = InstanceOfChecker("obj", str, "Объект", required=True)

        params = {}
        with pytest.raises(ValidationFieldError) as exc:
            checker.check(params)
        assert "Отсутствует обязательный параметр: 'obj'" in str(exc.value)

    def test_instanceof_required_with_none(self):
        """Обязательное поле с None -> ошибка."""
        checker = InstanceOfChecker("obj", str, "Объект", required=True)

        params = {"obj": None}
        with pytest.raises(ValidationFieldError) as exc:
            checker.check(params)
        assert "Отсутствует обязательный параметр: 'obj'" in str(exc.value)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Граничные случаи
    # ------------------------------------------------------------------

    def test_instanceof_with_none_for_not_required(self):
        """
        Необязательное поле с None -> проверка типа.
        None не является экземпляром указанного класса.
        """
        checker = InstanceOfChecker("obj", str, "Объект", required=False)

        params = {"obj": None}
        with pytest.raises(ValidationFieldError) as exc:
            checker.check(params)
        assert "должно быть экземпляром класса str" in str(exc.value)

    def test_instanceof_with_subclass(self):
        """Подкласс должен проходить проверку."""

        class Base:
            pass

        class Derived(Base):
            pass

        checker = InstanceOfChecker("obj", Base, "Базовый класс")

        params = {"obj": Derived()}
        checker.check(params)  # подкласс проходит

    def test_instanceof_with_tuple_containing_base_class(self):
        """Кортеж с базовым классом принимает подклассы."""

        class Base:
            pass

        class Derived(Base):
            pass

        checker = InstanceOfChecker("obj", (Base, int), "Базовый класс или число")

        params = {"obj": Derived()}
        checker.check(params)
