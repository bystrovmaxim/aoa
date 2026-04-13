# tests/checkers/test_result_instance_checker.py
"""
Тесты ResultInstanceChecker — чекер принадлежности значения указанному классу.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что ResultInstanceChecker корректно валидирует принадлежность
значения в словаре результата аспекта указанному классу (или одному
из классов, если передан кортеж). Использует isinstance() для проверки,
что означает поддержку наследования.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

TestValidValues
    - Экземпляр точного класса принимается.
    - Экземпляр дочернего класса принимается (наследование).
    - Кортеж классов — экземпляр любого из них принимается.
    - Встроенные типы (dict, list, str) принимаются.

TestInvalidValues
    - Экземпляр другого класса — ошибка.
    - Примитив вместо пользовательского класса — ошибка.
    - Кортеж классов — экземпляр вне кортежа — ошибка.
    - Сообщение об ошибке содержит имя поля и фактический тип.
    - Сообщение для кортежа содержит имена всех ожидаемых классов.

TestRequired
    - required=True: отсутствующее или None поле — ошибка.
    - required=False: отсутствующее или None поле допускается.
    - required=False: присутствующее значение неверного типа — ошибка.

TestExtraParams
    - _get_extra_params возвращает expected_class.

TestDecorator
    - result_instance записывает _checker_meta с корректными параметрами.
    - expected_class (одиночный и кортеж) попадает в extra_params.
    - Декоратор возвращает оригинальную функцию.
    - Несколько декораторов накапливаются.
"""

import pytest

from action_machine.intents.checkers.result_instance_checker import (
    ResultInstanceChecker,
    result_instance,
)
from action_machine.model.exceptions import ValidationFieldError

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы для тестов
# ═════════════════════════════════════════════════════════════════════════════


class _User:
    """Простой пользовательский класс для проверки isinstance."""

    def __init__(self, user_id: int, name: str) -> None:
        self.user_id = user_id
        self.name = name


class _AdminUser(_User):
    """Дочерний класс — проверяет поддержку наследования в isinstance."""

    def __init__(self, user_id: int, name: str, level: int) -> None:
        super().__init__(user_id, name)
        self.level = level


class _Order:
    """Класс заказа — используется для проверки несовпадения типов."""

    def __init__(self, order_id: str) -> None:
        self.order_id = order_id


class _Payment:
    """Класс оплаты — используется в кортеже ожидаемых классов."""

    def __init__(self, amount: float) -> None:
        self.amount = amount


# ═════════════════════════════════════════════════════════════════════════════
# Валидные значения
# ═════════════════════════════════════════════════════════════════════════════


class TestValidValues:
    """Проверяет, что экземпляры корректных классов принимаются без ошибок."""

    def test_exact_class_accepted(self):
        """Экземпляр точного класса принимается."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=True)
        user = _User(user_id=1, name="Alice")

        # Act & Assert — исключения нет
        checker.check({"user": user})

    def test_subclass_accepted(self):
        """Экземпляр дочернего класса принимается (isinstance проверяет наследование)."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=True)
        admin = _AdminUser(user_id=2, name="Bob", level=5)

        # Act & Assert — исключения нет
        checker.check({"user": admin})

    def test_tuple_of_classes_first_match(self):
        """Кортеж классов — экземпляр первого класса принимается."""
        # Arrange
        checker = ResultInstanceChecker("entity", (_User, _Order), required=True)
        user = _User(user_id=1, name="Alice")

        # Act & Assert — исключения нет
        checker.check({"entity": user})

    def test_tuple_of_classes_second_match(self):
        """Кортеж классов — экземпляр второго класса принимается."""
        # Arrange
        checker = ResultInstanceChecker("entity", (_User, _Order), required=True)
        order = _Order(order_id="ORD-001")

        # Act & Assert — исключения нет
        checker.check({"entity": order})

    def test_tuple_subclass_match(self):
        """Кортеж классов — дочерний класс одного из элементов принимается."""
        # Arrange
        checker = ResultInstanceChecker("entity", (_User, _Order), required=True)
        admin = _AdminUser(user_id=3, name="Carol", level=10)

        # Act & Assert — исключения нет
        checker.check({"entity": admin})

    def test_builtin_dict_accepted(self):
        """Встроенный тип dict принимается как expected_class."""
        # Arrange
        checker = ResultInstanceChecker("data", dict, required=True)

        # Act & Assert — исключения нет
        checker.check({"data": {"key": "value"}})

    def test_builtin_list_accepted(self):
        """Встроенный тип list принимается как expected_class."""
        # Arrange
        checker = ResultInstanceChecker("items", list, required=True)

        # Act & Assert — исключения нет
        checker.check({"items": [1, 2, 3]})

    def test_builtin_str_accepted(self):
        """Встроенный тип str принимается как expected_class."""
        # Arrange
        checker = ResultInstanceChecker("label", str, required=True)

        # Act & Assert — исключения нет
        checker.check({"label": "hello"})

    def test_tuple_of_builtins_accepted(self):
        """Кортеж встроенных типов — dict или list."""
        # Arrange
        checker = ResultInstanceChecker("data", (dict, list), required=True)

        # Act & Assert — оба варианта проходят
        checker.check({"data": {"a": 1}})
        checker.check({"data": [1, 2]})


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные значения
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidValues:
    """Проверяет отклонение значений неверного типа с выбросом ValidationFieldError."""

    def test_wrong_class_rejected(self):
        """Экземпляр другого класса отклоняется."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=True)
        order = _Order(order_id="ORD-001")

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"user": order})

    def test_primitive_instead_of_class_rejected(self):
        """Примитив (строка) вместо пользовательского класса отклоняется."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"user": "not a user"})

    def test_int_instead_of_class_rejected(self):
        """Целое число вместо пользовательского класса отклоняется."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"user": 42})

    def test_none_when_required_rejected(self):
        """None при required=True вызывает ошибку."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"user": None})

    def test_tuple_no_match_rejected(self):
        """Кортеж классов — экземпляр вне кортежа отклоняется."""
        # Arrange
        checker = ResultInstanceChecker("entity", (_User, _Order), required=True)
        payment = _Payment(amount=99.99)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"entity": payment})

    def test_dict_instead_of_custom_class_rejected(self):
        """Словарь вместо пользовательского класса отклоняется."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"user": {"user_id": 1, "name": "Alice"}})

    def test_error_message_single_class_contains_field_name(self):
        """Сообщение об ошибке для одного класса содержит имя поля."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="user"):
            checker.check({"user": "not a user"})

    def test_error_message_single_class_contains_expected_name(self):
        """Сообщение об ошибке содержит имя ожидаемого класса."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="_User"):
            checker.check({"user": "not a user"})

    def test_error_message_single_class_contains_actual_type(self):
        """Сообщение об ошибке содержит фактический тип значения."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="str"):
            checker.check({"user": "not a user"})

    def test_error_message_tuple_contains_all_class_names(self):
        """Сообщение об ошибке для кортежа содержит имена всех ожидаемых классов."""
        # Arrange
        checker = ResultInstanceChecker("entity", (_User, _Order), required=True)
        payment = _Payment(amount=99.99)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="_User"):
            checker.check({"entity": payment})

    def test_error_message_tuple_contains_second_class_name(self):
        """Сообщение об ошибке для кортежа содержит имя второго класса."""
        # Arrange
        checker = ResultInstanceChecker("entity", (_User, _Order), required=True)
        payment = _Payment(amount=99.99)

        # Act & Assert
        with pytest.raises(ValidationFieldError, match="_Order"):
            checker.check({"entity": payment})


# ═════════════════════════════════════════════════════════════════════════════
# Обязательность поля (required)
# ═════════════════════════════════════════════════════════════════════════════


class TestRequired:
    """Проверяет поведение флага required для обязательных и опциональных полей."""

    def test_required_missing_field_raises(self):
        """Отсутствующее обязательное поле вызывает ошибку."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({})

    def test_required_none_raises(self):
        """None в обязательном поле вызывает ошибку."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=True)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"user": None})

    def test_optional_missing_field_passes(self):
        """Отсутствующее опциональное поле допускается."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=False)

        # Act & Assert — исключения нет
        checker.check({})

    def test_optional_none_passes(self):
        """None в опциональном поле допускается."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=False)

        # Act & Assert — исключения нет
        checker.check({"user": None})

    def test_optional_invalid_type_still_raises(self):
        """Даже в опциональном поле значение неверного типа вызывает ошибку."""
        # Arrange
        checker = ResultInstanceChecker("user", _User, required=False)

        # Act & Assert
        with pytest.raises(ValidationFieldError):
            checker.check({"user": "not a user"})


# ═════════════════════════════════════════════════════════════════════════════
# Дополнительные параметры (_get_extra_params)
# ═════════════════════════════════════════════════════════════════════════════


class TestExtraParams:
    """Проверяет, что _get_extra_params возвращает expected_class."""

    def test_extra_params_single_class(self):
        """Одиночный класс сохраняется в extra_params."""
        # Arrange
        checker = ResultInstanceChecker("user", _User)

        # Act
        params = checker._get_extra_params()

        # Assert
        assert params["expected_class"] is _User

    def test_extra_params_tuple_of_classes(self):
        """Кортеж классов сохраняется в extra_params."""
        # Arrange
        expected = (_User, _Order)
        checker = ResultInstanceChecker("entity", expected)

        # Act
        params = checker._get_extra_params()

        # Assert
        assert params["expected_class"] is expected


# ═════════════════════════════════════════════════════════════════════════════
# Декоратор result_instance
# ═════════════════════════════════════════════════════════════════════════════


class TestDecorator:
    """Проверяет, что декоратор result_instance записывает метаданные в функцию."""

    def test_checker_meta_attached(self):
        """Декоратор создаёт атрибут _checker_meta."""
        # Arrange & Act
        @result_instance("user", _User)
        async def aspect(self, params, state, box, connections):
            return {"user": _User(1, "Alice")}

        # Assert
        assert hasattr(aspect, "_checker_meta")
        assert len(aspect._checker_meta) == 1

    def test_checker_class_is_result_instance_checker(self):
        """Метаданные содержат правильный класс чекера."""
        # Arrange & Act
        @result_instance("user", _User)
        async def aspect(self, params, state, box, connections):
            return {"user": _User(1, "Alice")}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["checker_class"] is ResultInstanceChecker

    def test_field_name_recorded(self):
        """Имя поля сохраняется в метаданных."""
        # Arrange & Act
        @result_instance("order", _Order)
        async def aspect(self, params, state, box, connections):
            return {"order": _Order("ORD-001")}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["field_name"] == "order"

    def test_required_default_true(self):
        """По умолчанию required=True."""
        # Arrange & Act
        @result_instance("user", _User)
        async def aspect(self, params, state, box, connections):
            return {"user": _User(1, "Alice")}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["required"] is True

    def test_required_false_recorded(self):
        """Явное required=False сохраняется."""
        # Arrange & Act
        @result_instance("user", _User, required=False)
        async def aspect(self, params, state, box, connections):
            return {"user": None}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["required"] is False

    def test_extra_params_single_class_in_meta(self):
        """Одиночный expected_class проверяется через экземпляр чекера."""
        # Arrange & Act
        @result_instance("user", _User)
        async def aspect(self, params, state, box, connections):
            return {"user": _User(1, "Alice")}

        # Assert — метаданные записаны корректно
        meta = aspect._checker_meta[0]
        assert meta["checker_class"] is ResultInstanceChecker
        assert meta["field_name"] == "user"
        # Дополнительные параметры проверяем через чекер
        checker = ResultInstanceChecker("user", _User)
        assert checker._get_extra_params()["expected_class"] is _User

    def test_extra_params_tuple_in_meta(self):
        """Кортеж expected_class проверяется через экземпляр чекера."""
        # Arrange
        expected = (_User, _Order)

        # Act
        @result_instance("entity", expected)
        async def aspect(self, params, state, box, connections):
            return {"entity": _User(1, "Alice")}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["checker_class"] is ResultInstanceChecker
        checker = ResultInstanceChecker("entity", expected)
        assert checker._get_extra_params()["expected_class"] is expected

    def test_decorator_returns_original_function(self):
        """Декоратор возвращает оригинальную функцию без изменений."""
        # Arrange
        async def original(self, params, state, box, connections):
            return {"user": _User(1, "Alice")}

        # Act
        decorated = result_instance("user", _User)(original)

        # Assert
        assert decorated is original

    def test_multiple_decorators_accumulate(self):
        """Несколько декораторов на одном методе создают список метаданных."""
        # Arrange & Act
        @result_instance("user", _User)
        @result_instance("order", _Order)
        async def aspect(self, params, state, box, connections):
            return {
                "user": _User(1, "Alice"),
                "order": _Order("ORD-001"),
            }

        # Assert
        assert len(aspect._checker_meta) == 2
        field_names = {m["field_name"] for m in aspect._checker_meta}
        assert field_names == {"user", "order"}

    def test_combined_with_builtin_types(self):
        """Декоратор работает со встроенными типами (dict, list)."""
        # Arrange & Act
        @result_instance("data", (dict, list))
        async def aspect(self, params, state, box, connections):
            return {"data": {"key": "value"}}

        # Assert
        meta = aspect._checker_meta[0]
        assert meta["checker_class"] is ResultInstanceChecker
        assert meta["field_name"] == "data"
        checker = ResultInstanceChecker("data", (dict, list))
        assert checker._get_extra_params()["expected_class"] == (dict, list)
