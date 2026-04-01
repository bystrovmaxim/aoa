# tests2/logging/test_sensitive_decorator.py
"""
Тесты декоратора @sensitive и функции маскирования значений.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @sensitive помечает свойство (property) класса как содержащее
чувствительные данные. При подстановке значения в шаблон лога система
обнаруживает конфигурацию @sensitive и автоматически маскирует значение
по заданным правилам.

Алгоритм маскирования:
    visible = min(max_chars, ceil(len(value) * max_percent / 100))
    Если visible >= len(value) → строка без изменений.
    Иначе: первые visible символов + char * 5.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Применение к свойству (property) в любом порядке с @property.
- Сохранение конфигурации в _sensitive_config getter-функции.
- Поддержка параметров: enabled, max_chars, char, max_percent.
- Маскирование строк, чисел, булевых значений.
- Отключение маскирования через enabled=False.
- Обработка пустых и коротких строк.
- Параметры по умолчанию.
- Ошибки при невалидных аргументах.
"""

import pytest

from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta
from action_machine.logging.masking import mask_value
from action_machine.logging.sensitive_decorator import sensitive
from action_machine.resource_managers.base_resource_manager import BaseResourceManager


# ======================================================================
# ТЕСТЫ: Валидное применение декоратора
# ======================================================================


class TestValidUsage:
    """Декоратор корректно записывает конфигурацию."""

    def test_property_then_sensitive(self) -> None:
        """
        @property + @sensitive — стандартный порядок.
        Конфигурация записывается в fget свойства.
        """
        class Account:
            def __init__(self, email: str):
                self._email = email

            @property
            @sensitive(True, max_chars=3, char="*", max_percent=50)
            def email(self) -> str:
                return self._email

        prop = Account.__dict__["email"]
        assert isinstance(prop, property)
        assert hasattr(prop.fget, "_sensitive_config")
        config = prop.fget._sensitive_config
        assert config["enabled"] is True
        assert config["max_chars"] == 3
        assert config["char"] == "*"
        assert config["max_percent"] == 50

    def test_sensitive_then_property(self) -> None:
        """
        @sensitive + @property — обратный порядок.
        Декоратор применяется к property, извлекает fget и записывает конфиг.
        """
        class Account:
            def __init__(self, phone: str):
                self._phone = phone

            @sensitive(True, max_chars=4, char="#", max_percent=100)
            @property
            def phone(self) -> str:
                return self._phone

        prop = Account.__dict__["phone"]
        assert isinstance(prop, property)
        assert hasattr(prop.fget, "_sensitive_config")
        config = prop.fget._sensitive_config
        assert config["max_chars"] == 4
        assert config["char"] == "#"

    def test_enabled_false(self) -> None:
        """
        @sensitive(False) — конфигурация записывается, но enabled=False.
        Маскирование не применяется.
        """
        class Account:
            @property
            @sensitive(False)
            def name(self) -> str:
                return "John"

        config = Account.__dict__["name"].fget._sensitive_config
        assert config["enabled"] is False

    def test_default_parameters(self) -> None:
        """
        @sensitive() с дефолтами: enabled=True, max_chars=3, char='*', max_percent=50.
        """
        class Account:
            @property
            @sensitive()
            def secret(self) -> str:
                return "top_secret"

        config = Account.__dict__["secret"].fget._sensitive_config
        assert config["enabled"] is True
        assert config["max_chars"] == 3
        assert config["char"] == "*"
        assert config["max_percent"] == 50

    def test_applied_to_callable(self) -> None:
        """
        @sensitive на обычной функции (не property) — конфигурация записывается.
        Используется для поддержки обратного порядка декораторов.
        """
        @sensitive(True, max_chars=5)
        def getter(self):
            return "value"

        assert hasattr(getter, "_sensitive_config")
        assert getter._sensitive_config["max_chars"] == 5


# ======================================================================
# ТЕСТЫ: Невалидные аргументы
# ======================================================================


class TestInvalidArgs:
    """Невалидные аргументы → TypeError или ValueError."""

    def test_enabled_not_bool_raises(self) -> None:
        """enabled должен быть bool."""
        with pytest.raises(TypeError, match="enabled должен быть bool"):
            sensitive("yes")

    def test_max_chars_not_int_raises(self) -> None:
        """max_chars должен быть int."""
        with pytest.raises(TypeError, match="max_chars должен быть int"):
            sensitive(True, max_chars="3")

    def test_max_chars_negative_raises(self) -> None:
        """max_chars не может быть отрицательным."""
        with pytest.raises(ValueError, match="не может быть отрицательным"):
            sensitive(True, max_chars=-1)

    def test_char_not_string_raises(self) -> None:
        """char должен быть строкой."""
        with pytest.raises(TypeError, match="char должен быть строкой"):
            sensitive(True, char=42)

    def test_char_multiple_chars_raises(self) -> None:
        """char должен быть одним символом."""
        with pytest.raises(ValueError, match="одним символом"):
            sensitive(True, char="**")

    def test_char_empty_raises(self) -> None:
        """char не может быть пустой строкой."""
        with pytest.raises(ValueError, match="одним символом"):
            sensitive(True, char="")

    def test_max_percent_not_int_raises(self) -> None:
        """max_percent должен быть int."""
        with pytest.raises(TypeError, match="max_percent должен быть int"):
            sensitive(True, max_percent="50")

    def test_max_percent_negative_raises(self) -> None:
        """max_percent не может быть отрицательным."""
        with pytest.raises(ValueError, match="в диапазоне 0..100"):
            sensitive(True, max_percent=-1)

    def test_max_percent_over_100_raises(self) -> None:
        """max_percent не может быть больше 100."""
        with pytest.raises(ValueError, match="в диапазоне 0..100"):
            sensitive(True, max_percent=101)


# ======================================================================
# ТЕСТЫ: Невалидные цели
# ======================================================================


class TestInvalidTarget:
    """Декоратор применён к невалидной цели → TypeError."""

    def test_applied_to_string_raises(self) -> None:
        """Цель должна быть property или callable."""
        with pytest.raises(TypeError, match="только к свойствам"):
            sensitive()("not_a_function")

    def test_applied_to_int_raises(self) -> None:
        """Цель должна быть property или callable."""
        with pytest.raises(TypeError, match="только к свойствам"):
            sensitive()(42)


# ======================================================================
# ТЕСТЫ: Функция mask_value
# ======================================================================


class TestMaskValue:
    """Функция mask_value применяет маскирование по конфигурации."""

    def test_short_string_masked(self) -> None:
        """
        "maxim@example.com" с max_chars=3, max_percent=50 → "max*****".
        len=18, by_chars=min(3,18)=3, by_percent=ceil(18*50/100)=9,
        keep=min(3,9)=3. Первые 3 символа + 5 звёздочек.
        """
        config = {"max_chars": 3, "char": "*", "max_percent": 50}
        result = mask_value("maxim@example.com", config)
        assert result == "max*****"

    def test_max_percent_limits_visible(self) -> None:
        """
        "abcd" с max_chars=10, max_percent=25 → "a*****".
        len=4, by_chars=min(10,4)=4, by_percent=ceil(4*25/100)=1,
        keep=min(4,1)=1.
        """
        config = {"max_chars": 10, "char": "*", "max_percent": 25}
        result = mask_value("abcd", config)
        assert result == "a*****"

    def test_custom_char(self) -> None:
        """Маскирование с char='#' вместо '*'."""
        config = {"max_chars": 2, "char": "#", "max_percent": 50}
        result = mask_value("secret", config)
        assert result == "se#####"

    def test_full_visible_when_keep_exceeds_length(self) -> None:
        """Если keep >= len(value), строка возвращается без изменений."""
        config = {"max_chars": 10, "char": "*", "max_percent": 100}
        result = mask_value("ab", config)
        assert result == "ab"

    def test_empty_string(self) -> None:
        """Пустая строка — пустая строка (нечего маскировать)."""
        config = {"max_chars": 3, "char": "*", "max_percent": 50}
        result = mask_value("", config)
        assert result == ""

    def test_zero_max_chars(self) -> None:
        """max_chars=0 → ни одного видимого символа, только маска."""
        config = {"max_chars": 0, "char": "*", "max_percent": 50}
        result = mask_value("secret", config)
        assert result == "*****"

    def test_numeric_value(self) -> None:
        """Числовые значения преобразуются в строку и маскируются."""
        config = {"max_chars": 2, "char": "*", "max_percent": 50}
        result = mask_value(123456, config)
        assert result == "12*****"

    def test_boolean_value(self) -> None:
        """Булевы значения преобразуются в строку и маскируются."""
        config = {"max_chars": 1, "char": "*", "max_percent": 50}
        result = mask_value(True, config)
        assert result == "T*****"


# ======================================================================
# ТЕСТЫ: Интеграция с MetadataBuilder
# ======================================================================


class TestMetadataIntegration:
    """MetadataBuilder собирает SensitiveFieldMeta из _sensitive_config."""

    def test_sensitive_field_in_metadata(self) -> None:
        """
        Свойство с @sensitive включается в ClassMetadata.sensitive_fields.
        """
        @meta(description="Менеджер с чувствительными данными")
        class Manager(BaseResourceManager):
            def __init__(self):
                self._token = "secret-token"

            @property
            @sensitive(True, max_chars=3)
            def token(self) -> str:
                return self._token

            def get_wrapper_class(self):
                return None

        coordinator = GateCoordinator()
        metadata = coordinator.get(Manager)

        assert metadata.has_sensitive_fields()
        assert len(metadata.sensitive_fields) == 1
        sf = metadata.sensitive_fields[0]
        assert sf.property_name == "token"
        assert sf.config["enabled"] is True
        assert sf.config["max_chars"] == 3

    def test_disabled_sensitive_in_metadata(self) -> None:
        """
        @sensitive(False) — поле включается в metadata, но enabled=False.
        """
        @meta(description="Менеджер")
        class Manager(BaseResourceManager):
            @property
            @sensitive(False)
            def name(self) -> str:
                return "public"

            def get_wrapper_class(self):
                return None

        coordinator = GateCoordinator()
        metadata = coordinator.get(Manager)

        assert metadata.has_sensitive_fields()
        assert metadata.sensitive_fields[0].config["enabled"] is False