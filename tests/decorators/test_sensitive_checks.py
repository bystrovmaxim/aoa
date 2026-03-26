# tests/decorators/test_sensitive_checks.py
"""
Тесты проверок декоратора @sensitive.

Покрывают все инварианты, объявленные в sensitive_decorator.py:
    - Применение к свойству в порядке @property → @sensitive — успех.
    - Применение к свойству в порядке @sensitive → @property — успех.
    - Конфигурация маскирования сохраняется корректно.
    - Маскированное свойство возвращает оригинальное значение при прямом вызове.
    - enabled не bool — TypeError.
    - max_chars не int — TypeError.
    - max_chars отрицательный — ValueError.
    - char не строка — TypeError.
    - char не один символ — ValueError.
    - max_percent не int — TypeError.
    - max_percent вне диапазона — ValueError.
    - Применение к не-callable/не-property — TypeError.
    - Property без getter — TypeError.
"""

import pytest

from action_machine.logging.sensitive_decorator import sensitive

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные классы
# ─────────────────────────────────────────────────────────────────────────────

class AccountPropertyFirst:
    """Класс с порядком @property → @sensitive (рекомендуемый)."""

    def __init__(self, email: str, phone: str):
        self._email = email
        self._phone = phone

    @property
    @sensitive(True, max_chars=3, char='*', max_percent=50)
    def email(self) -> str:
        return self._email

    @property
    @sensitive(True, max_chars=4, char='#', max_percent=100)
    def phone(self) -> str:
        return self._phone


class AccountSensitiveFirst:
    """Класс с порядком @sensitive → @property (тоже поддерживается)."""

    def __init__(self, email: str):
        self._email = email

    @sensitive(True, max_chars=3, char='*', max_percent=50)
    @property
    def email(self) -> str:
        return self._email


# ─────────────────────────────────────────────────────────────────────────────
# Успешные сценарии: порядок @property → @sensitive
# ─────────────────────────────────────────────────────────────────────────────

class TestSensitivePropertyFirstSuccess:
    """Проверка корректного применения @sensitive под @property."""

    def test_config_attached_to_getter(self):
        """_sensitive_config прикрепляется к getter функции."""
        # Получаем property-дескриптор из класса
        prop = AccountPropertyFirst.__dict__['email']
        assert isinstance(prop, property)
        assert hasattr(prop.fget, '_sensitive_config')

    def test_config_values(self):
        """Значения конфигурации совпадают с переданными."""
        prop = AccountPropertyFirst.__dict__['email']
        config = prop.fget._sensitive_config
        assert config["enabled"] is True
        assert config["max_chars"] == 3
        assert config["char"] == '*'
        assert config["max_percent"] == 50

    def test_phone_config_values(self):
        """Второе свойство имеет свою конфигурацию."""
        prop = AccountPropertyFirst.__dict__['phone']
        config = prop.fget._sensitive_config
        assert config["max_chars"] == 4
        assert config["char"] == '#'
        assert config["max_percent"] == 100

    def test_property_still_works(self):
        """Свойство возвращает оригинальное значение при прямом вызове."""
        account = AccountPropertyFirst(email="test@example.com", phone="+1234567890")
        assert account.email == "test@example.com"
        assert account.phone == "+1234567890"

    def test_property_is_readonly(self):
        """Свойство остаётся readonly (без setter)."""
        account = AccountPropertyFirst(email="test@example.com", phone="+1234567890")
        with pytest.raises(AttributeError):
            account.email = "other@example.com"


# ─────────────────────────────────────────────────────────────────────────────
# Успешные сценарии: порядок @sensitive → @property
# ─────────────────────────────────────────────────────────────────────────────

class TestSensitiveSensitiveFirstSuccess:
    """Проверка корректного применения @sensitive над @property."""

    def test_config_attached(self):
        """_sensitive_config прикрепляется при порядке @sensitive → @property."""
        prop = AccountSensitiveFirst.__dict__['email']
        assert isinstance(prop, property)
        assert hasattr(prop.fget, '_sensitive_config')

    def test_config_values(self):
        """Значения конфигурации корректны."""
        prop = AccountSensitiveFirst.__dict__['email']
        config = prop.fget._sensitive_config
        assert config["enabled"] is True
        assert config["max_chars"] == 3
        assert config["char"] == '*'
        assert config["max_percent"] == 50

    def test_property_still_works(self):
        """Свойство возвращает оригинальное значение."""
        account = AccountSensitiveFirst(email="test@example.com")
        assert account.email == "test@example.com"


# ─────────────────────────────────────────────────────────────────────────────
# Успешные сценарии: конфигурация по умолчанию
# ─────────────────────────────────────────────────────────────────────────────

class TestSensitiveDefaults:
    """Проверка значений по умолчанию."""

    def test_default_config(self):
        """Без аргументов — значения по умолчанию."""

        @property
        @sensitive()
        def secret(self) -> str:
            return "hidden"

        config = secret.fget._sensitive_config
        assert config["enabled"] is True
        assert config["max_chars"] == 3
        assert config["char"] == '*'
        assert config["max_percent"] == 50

    def test_disabled(self):
        """enabled=False сохраняется."""

        @property
        @sensitive(False)
        def secret(self) -> str:
            return "visible"

        config = secret.fget._sensitive_config
        assert config["enabled"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: неправильный enabled
# ─────────────────────────────────────────────────────────────────────────────

class TestSensitiveEnabledErrors:
    """Проверка ошибок при некорректном enabled."""

    def test_string_enabled_raises(self):
        """Строка вместо bool — TypeError."""
        with pytest.raises(TypeError, match="enabled должен быть bool"):
            sensitive("yes")

    def test_int_enabled_raises(self):
        """Число вместо bool — TypeError."""
        with pytest.raises(TypeError, match="enabled должен быть bool"):
            sensitive(1)

    def test_none_enabled_raises(self):
        """None вместо bool — TypeError."""
        with pytest.raises(TypeError, match="enabled должен быть bool"):
            sensitive(None)


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: неправильный max_chars
# ─────────────────────────────────────────────────────────────────────────────

class TestSensitiveMaxCharsErrors:
    """Проверка ошибок при некорректном max_chars."""

    def test_string_max_chars_raises(self):
        """Строка вместо int — TypeError."""
        with pytest.raises(TypeError, match="max_chars должен быть int"):
            sensitive(True, max_chars="3")

    def test_negative_max_chars_raises(self):
        """Отрицательное значение — ValueError."""
        with pytest.raises(ValueError, match="max_chars не может быть отрицательным"):
            sensitive(True, max_chars=-1)

    def test_float_max_chars_raises(self):
        """float вместо int — TypeError."""
        with pytest.raises(TypeError, match="max_chars должен быть int"):
            sensitive(True, max_chars=3.5)


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: неправильный char
# ─────────────────────────────────────────────────────────────────────────────

class TestSensitiveCharErrors:
    """Проверка ошибок при некорректном char."""

    def test_int_char_raises(self):
        """Число вместо строки — TypeError."""
        with pytest.raises(TypeError, match="char должен быть строкой"):
            sensitive(True, char=42)

    def test_empty_char_raises(self):
        """Пустая строка — ValueError."""
        with pytest.raises(ValueError, match="char должен быть одним символом"):
            sensitive(True, char="")

    def test_multiple_chars_raises(self):
        """Несколько символов — ValueError."""
        with pytest.raises(ValueError, match="char должен быть одним символом"):
            sensitive(True, char="**")

    def test_none_char_raises(self):
        """None вместо строки — TypeError."""
        with pytest.raises(TypeError, match="char должен быть строкой"):
            sensitive(True, char=None)


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: неправильный max_percent
# ─────────────────────────────────────────────────────────────────────────────

class TestSensitiveMaxPercentErrors:
    """Проверка ошибок при некорректном max_percent."""

    def test_string_max_percent_raises(self):
        """Строка вместо int — TypeError."""
        with pytest.raises(TypeError, match="max_percent должен быть int"):
            sensitive(True, max_percent="50")

    def test_negative_max_percent_raises(self):
        """Отрицательное значение — ValueError."""
        with pytest.raises(ValueError, match="max_percent должен быть в диапазоне"):
            sensitive(True, max_percent=-1)

    def test_over_100_max_percent_raises(self):
        """Значение больше 100 — ValueError."""
        with pytest.raises(ValueError, match="max_percent должен быть в диапазоне"):
            sensitive(True, max_percent=101)

    def test_float_max_percent_raises(self):
        """float вместо int — TypeError."""
        with pytest.raises(TypeError, match="max_percent должен быть int"):
            sensitive(True, max_percent=50.0)


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: неправильная цель декоратора
# ─────────────────────────────────────────────────────────────────────────────

class TestSensitiveTargetErrors:
    """Проверка ошибок при применении к неправильным целям."""

    def test_applied_to_string_raises(self):
        """Строка — TypeError."""
        with pytest.raises(TypeError, match="только к свойствам"):
            sensitive(True)("not a function")

    def test_applied_to_number_raises(self):
        """Число — TypeError."""
        with pytest.raises(TypeError, match="только к свойствам"):
            sensitive(True)(42)

    def test_applied_to_none_raises(self):
        """None — TypeError."""
        with pytest.raises(TypeError, match="только к свойствам"):
            sensitive(True)(None)

    def test_applied_to_regular_method(self):
        """Обычный метод (не property) — _sensitive_config прикрепляется,
        но ошибка будет обнаружена позже в билдере при сборке метаданных,
        так как на этапе декорирования callable проходит проверку."""

        @sensitive(True, max_chars=3)
        def regular_method(self):
            return "value"

        # Декоратор прикрепляет конфиг — это допустимо на этом этапе
        assert hasattr(regular_method, '_sensitive_config')

    def test_property_without_getter_raises(self):
        """Property без getter — TypeError."""
        # Создаём property с setter но без getter
        prop = property(None, lambda self, v: None)
        with pytest.raises(TypeError, match="без getter"):
            sensitive(True)(prop)
