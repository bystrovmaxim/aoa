# tests/decorators/test_sensitive_decorator.py
"""
Тесты декоратора @sensitive — маскирование чувствительных данных в логах.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @sensitive помечает свойство (property) класса как содержащее
чувствительные данные. При подстановке значения в шаблон лога система
обнаруживает конфигурацию @sensitive и автоматически маскирует значение.

Декоратор записывает конфигурацию маскирования в атрибут _sensitive_config
на getter-функции свойства. MetadataBuilder._collect_sensitive_fields(cls)
находит этот атрибут и включает поле в ClassMetadata.sensitive_fields.

Алгоритм маскирования:
    visible = min(max_chars, ceil(len(value) * max_percent / 100))
    Если visible >= len(value) → строка без изменений.
    Иначе: первые visible символов + char * 5.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Валидное применение:
    - @property + @sensitive — стандартный порядок.
    - @sensitive + @property — обратный порядок.
    - Параметры: enabled, max_chars, char, max_percent.
    - enabled=False — маскирование отключено.

Запись _sensitive_config:
    - Конфигурация записывается в fget свойства.
    - MetadataBuilder собирает SensitiveFieldMeta.

Невалидные аргументы:
    - enabled не bool → TypeError.
    - max_chars не int → TypeError.
    - max_chars < 0 → ValueError.
    - char не строка → TypeError.
    - char не один символ → ValueError.
    - max_percent не int → TypeError.
    - max_percent вне 0..100 → ValueError.

Невалидные цели:
    - Не callable и не property → TypeError.

Маскирование значений:
    - Короткая строка — частичная маскировка.
    - Длинная строка — ограничение по max_chars и max_percent.
    - Пустая строка — без маскировки.
"""

import pytest

from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta
from action_machine.logging.masking import mask_value
from action_machine.logging.sensitive_decorator import sensitive
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

# ═════════════════════════════════════════════════════════════════════════════
# Валидное применение
# ═════════════════════════════════════════════════════════════════════════════


class TestValidUsage:
    """Декоратор корректно записывает _sensitive_config на свойства."""

    def test_property_then_sensitive(self) -> None:
        """
        @property + @sensitive — стандартный порядок декораторов.

        @sensitive применяется к callable (getter), затем @property
        оборачивает его. Конфигурация записывается в fget.
        """
        # Arrange & Act
        class _Account:
            def __init__(self, email: str):
                self._email = email

            @property
            @sensitive(True, max_chars=3, char="*", max_percent=50)
            def email(self) -> str:
                return self._email

        # Assert — _sensitive_config на getter
        prop = _Account.__dict__["email"]
        assert isinstance(prop, property)
        assert hasattr(prop.fget, "_sensitive_config")
        config = prop.fget._sensitive_config
        assert config["enabled"] is True
        assert config["max_chars"] == 3
        assert config["char"] == "*"
        assert config["max_percent"] == 50

    def test_sensitive_then_property(self) -> None:
        """
        @sensitive + @property — обратный порядок декораторов.

        @sensitive применяется к property-объекту, извлекает fget,
        записывает конфигурацию и возвращает новый property.
        """
        # Arrange & Act
        class _Account:
            def __init__(self, phone: str):
                self._phone = phone

            @sensitive(True, max_chars=4, char="#", max_percent=100)
            @property
            def phone(self) -> str:
                return self._phone

        # Assert — _sensitive_config на getter
        prop = _Account.__dict__["phone"]
        assert isinstance(prop, property)
        assert hasattr(prop.fget, "_sensitive_config")
        config = prop.fget._sensitive_config
        assert config["max_chars"] == 4
        assert config["char"] == "#"

    def test_enabled_false(self) -> None:
        """
        @sensitive(False) — конфигурация записывается, но enabled=False.

        При enabled=False маскирование не применяется, значение
        выводится как есть. Полезно для временного отключения.
        """
        # Arrange & Act
        class _Account:
            @property
            @sensitive(False)
            def name(self) -> str:
                return "John"

        # Assert — enabled=False в конфигурации
        config = _Account.__dict__["name"].fget._sensitive_config
        assert config["enabled"] is False

    def test_default_parameters(self) -> None:
        """
        @sensitive() с дефолтами: enabled=True, max_chars=3, char='*', max_percent=50.
        """
        # Arrange & Act
        class _Account:
            @property
            @sensitive()
            def secret(self) -> str:
                return "top_secret"

        # Assert — дефолтные значения
        config = _Account.__dict__["secret"].fget._sensitive_config
        assert config["enabled"] is True
        assert config["max_chars"] == 3
        assert config["char"] == "*"
        assert config["max_percent"] == 50

    def test_applied_to_callable(self) -> None:
        """
        @sensitive на callable (функции) — записывает _sensitive_config напрямую.

        Это позволяет применить @sensitive перед @property в любом порядке.
        """
        # Arrange & Act
        @sensitive(True, max_chars=5)
        def getter(self):
            return "value"

        # Assert — _sensitive_config на функции
        assert hasattr(getter, "_sensitive_config")
        assert getter._sensitive_config["max_chars"] == 5


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные аргументы
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidArgs:
    """Невалидные аргументы → TypeError или ValueError."""

    def test_enabled_not_bool_raises(self) -> None:
        """
        @sensitive("yes") → TypeError.

        enabled должен быть bool.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="enabled должен быть bool"):
            sensitive("yes")

    def test_max_chars_not_int_raises(self) -> None:
        """
        @sensitive(max_chars="3") → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="max_chars должен быть int"):
            sensitive(True, max_chars="3")

    def test_max_chars_negative_raises(self) -> None:
        """
        @sensitive(max_chars=-1) → ValueError.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="не может быть отрицательным"):
            sensitive(True, max_chars=-1)

    def test_char_not_string_raises(self) -> None:
        """
        @sensitive(char=42) → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="char должен быть строкой"):
            sensitive(True, char=42)

    def test_char_multiple_chars_raises(self) -> None:
        """
        @sensitive(char="**") → ValueError.

        char должен быть одним символом.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="одним символом"):
            sensitive(True, char="**")

    def test_char_empty_raises(self) -> None:
        """
        @sensitive(char="") → ValueError.

        Пустая строка — не один символ.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="одним символом"):
            sensitive(True, char="")

    def test_max_percent_not_int_raises(self) -> None:
        """
        @sensitive(max_percent="50") → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="max_percent должен быть int"):
            sensitive(True, max_percent="50")

    def test_max_percent_negative_raises(self) -> None:
        """
        @sensitive(max_percent=-1) → ValueError.

        max_percent в диапазоне 0..100.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="в диапазоне 0..100"):
            sensitive(True, max_percent=-1)

    def test_max_percent_over_100_raises(self) -> None:
        """
        @sensitive(max_percent=101) → ValueError.
        """
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="в диапазоне 0..100"):
            sensitive(True, max_percent=101)


# ═════════════════════════════════════════════════════════════════════════════
# Невалидные цели
# ═════════════════════════════════════════════════════════════════════════════


class TestInvalidTarget:
    """Декоратор применён к невалидной цели → TypeError."""

    def test_applied_to_string_raises(self) -> None:
        """
        sensitive()("строка") → TypeError.

        Цель должна быть property или callable.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="только к свойствам"):
            sensitive()("not_a_function")

    def test_applied_to_int_raises(self) -> None:
        """
        sensitive()(42) → TypeError.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="только к свойствам"):
            sensitive()(42)


# ═════════════════════════════════════════════════════════════════════════════
# Маскирование значений (функция mask_value)
# ═════════════════════════════════════════════════════════════════════════════


class TestMaskValue:
    """Функция mask_value применяет маскирование по конфигурации."""

    def test_short_string_masked(self) -> None:
        """
        "maxim@example.com" с max_chars=3, max_percent=50 → "max*****".

        len=18, by_chars=min(3,18)=3, by_percent=ceil(18*50/100)=9,
        keep=min(3,9)=3. Первые 3 символа + 5 звёздочек.
        """
        # Arrange
        config = {"max_chars": 3, "char": "*", "max_percent": 50}

        # Act
        result = mask_value("maxim@example.com", config)

        # Assert
        assert result == "max*****"

    def test_max_percent_limits_visible(self) -> None:
        """
        "abcd" с max_chars=10, max_percent=25 → "a*****".

        len=4, by_chars=min(10,4)=4, by_percent=ceil(4*25/100)=1,
        keep=min(4,1)=1. Первый символ + 5 звёздочек.
        """
        # Arrange
        config = {"max_chars": 10, "char": "*", "max_percent": 25}

        # Act
        result = mask_value("abcd", config)

        # Assert
        assert result == "a*****"

    def test_custom_char(self) -> None:
        """
        Маскирование с char="#" вместо "*".
        """
        # Arrange
        config = {"max_chars": 2, "char": "#", "max_percent": 50}

        # Act
        result = mask_value("secret", config)

        # Assert — # вместо *
        assert result == "se#####"

    def test_full_visible_when_keep_exceeds_length(self) -> None:
        """
        "ab" с max_chars=10, max_percent=100 → "ab" (без маскировки).

        keep=min(10,2)=2, 2 >= len("ab")=2 → строка без изменений.
        """
        # Arrange
        config = {"max_chars": 10, "char": "*", "max_percent": 100}

        # Act
        result = mask_value("ab", config)

        # Assert — строка без маскировки
        assert result == "ab"

    def test_empty_string(self) -> None:
        """
        "" — пустая строка → пустая строка (нечего маскировать).
        """
        # Arrange
        config = {"max_chars": 3, "char": "*", "max_percent": 50}

        # Act
        result = mask_value("", config)

        # Assert
        assert result == ""

    def test_zero_max_chars(self) -> None:
        """
        max_chars=0 → ни одного видимого символа, только маска.
        """
        # Arrange
        config = {"max_chars": 0, "char": "*", "max_percent": 50}

        # Act
        result = mask_value("secret", config)

        # Assert — 0 видимых + 5 звёздочек
        assert result == "*****"


# ═════════════════════════════════════════════════════════════════════════════
# Интеграция с MetadataBuilder
# ═════════════════════════════════════════════════════════════════════════════


class TestMetadataIntegration:
    """MetadataBuilder собирает SensitiveFieldMeta из _sensitive_config."""

    def test_sensitive_field_in_metadata(self) -> None:
        """
        Свойство с @sensitive включается в ClassMetadata.sensitive_fields.
        """
        # Arrange
        @meta(description="Менеджер с чувствительными данными")
        class _Manager(BaseResourceManager):
            def __init__(self):
                self._token = "secret-token"

            @property
            @sensitive(True, max_chars=3)
            def token(self) -> str:
                return self._token

            def get_wrapper_class(self):
                return None

        coordinator = GateCoordinator()

        # Act
        metadata = coordinator.get(_Manager)

        # Assert — sensitive_fields содержит token
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
        # Arrange
        @meta(description="Менеджер")
        class _Manager(BaseResourceManager):
            @property
            @sensitive(False)
            def name(self) -> str:
                return "public"

            def get_wrapper_class(self):
                return None

        coordinator = GateCoordinator()

        # Act
        metadata = coordinator.get(_Manager)

        # Assert — поле в metadata, enabled=False
        assert metadata.has_sensitive_fields()
        assert metadata.sensitive_fields[0].config["enabled"] is False
