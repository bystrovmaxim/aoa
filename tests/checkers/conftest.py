"""
Общие фикстуры для тестирования чекеров полей.
"""

from datetime import datetime

import pytest

# ======================================================================
# ТЕСТОВЫЕ КЛАССЫ
# ======================================================================


class User:
    """Тестовый класс для InstanceOfChecker."""

    pass


class Admin:
    """Тестовый класс для InstanceOfChecker."""

    pass


# ======================================================================
# ФИКСТУРЫ С ВАЛИДНЫМИ ЗНАЧЕНИЯМИ
# ======================================================================


@pytest.fixture
def valid_string_params():
    """Параметры с валидной строкой."""
    return {"name": "John"}


@pytest.fixture
def valid_int_params():
    """Параметры с валидным целым числом."""
    return {"age": 25}


@pytest.fixture
def valid_float_params():
    """Параметры с валидным числом с плавающей точкой."""
    return {"price": 99.99}


@pytest.fixture
def valid_bool_params():
    """Параметры с валидным булевым значением."""
    return {"active": True}


@pytest.fixture
def valid_date_params():
    """Параметры с валидной датой."""
    return {"created": datetime(2024, 1, 1)}


@pytest.fixture
def valid_instance_params():
    """Параметры с валидным экземпляром класса."""
    return {"user": User()}


# ======================================================================
# ФИКСТУРЫ С НЕВАЛИДНЫМИ ЗНАЧЕНИЯМИ
# ======================================================================


@pytest.fixture
def wrong_type_string_params():
    """Параметры с неверным типом для строки."""
    return {"name": 123}


@pytest.fixture
def wrong_type_int_params():
    """Параметры с неверным типом для целого числа."""
    return {"age": "25"}


@pytest.fixture
def wrong_type_float_params():
    """Параметры с неверным типом для float."""
    return {"price": "100"}


@pytest.fixture
def wrong_type_bool_params():
    """Параметры с неверным типом для bool."""
    return [
        {"active": 1},
        {"active": 0},
        {"active": "true"},
        {"active": "false"},
        {"active": "yes"},
        {"active": []},
        {"active": {}},
    ]


@pytest.fixture
def wrong_type_date_params():
    """Параметры с неверным типом для даты."""
    return {"created": 12345}


@pytest.fixture
def wrong_type_instance_params():
    """Параметры с неверным типом для InstanceOfChecker."""
    return {"user": "not a user"}
