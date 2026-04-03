# tests/on_error/test_on_error_decorator.py
"""
Тесты декоратора @on_error.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет валидацию аргументов декоратора @on_error:
- Корректные аргументы → метод декорируется, _on_error_meta записывается.
- Некорректные типы исключений → TypeError.
- Пустое или отсутствующее description → ValueError/TypeError.
- Синхронный метод → TypeError.
- Неверное число параметров → TypeError.
- Имя метода без суффикса "_on_error" → NamingSuffixError.

Все тесты используют намеренно сломанные функции, определённые внутри
тестов, потому что они заведомо не могут быть частью рабочей доменной модели.
"""

import pytest

from action_machine.core.exceptions import NamingSuffixError
from action_machine.on_error import on_error

# ═════════════════════════════════════════════════════════════════════════════
# Успешное декорирование
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorDecoratorSuccess:
    """Тесты успешного применения @on_error к корректным методам."""

    def test_single_exception_type(self) -> None:
        """Один тип исключения → метод декорируется, _on_error_meta содержит кортеж из одного типа."""

        # Arrange — определяем async-метод с правильной сигнатурой и суффиксом
        @on_error(ValueError, description="Обработка ValueError")
        async def handle_value_on_error(self, params, state, box, connections, error):
            pass

        # Assert — метаданные записаны корректно
        assert hasattr(handle_value_on_error, "_on_error_meta")
        meta = handle_value_on_error._on_error_meta
        assert meta["exception_types"] == (ValueError,)
        assert meta["description"] == "Обработка ValueError"

    def test_tuple_of_exception_types(self) -> None:
        """Кортеж типов исключений → все типы сохраняются в _on_error_meta."""

        # Arrange — кортеж из двух типов
        @on_error((ValueError, TypeError), description="Обработка нескольких типов")
        async def handle_multi_on_error(self, params, state, box, connections, error):
            pass

        # Assert — оба типа в кортеже
        meta = handle_multi_on_error._on_error_meta
        assert meta["exception_types"] == (ValueError, TypeError)
        assert meta["description"] == "Обработка нескольких типов"

    def test_custom_exception_type(self) -> None:
        """Пользовательский тип исключения (наследник Exception) → принимается."""

        # Arrange — кастомное исключение
        class MyCustomError(Exception):
            pass

        @on_error(MyCustomError, description="Кастомная ошибка")
        async def handle_custom_on_error(self, params, state, box, connections, error):
            pass

        # Assert
        meta = handle_custom_on_error._on_error_meta
        assert meta["exception_types"] == (MyCustomError,)

    def test_method_returns_unchanged(self) -> None:
        """Декоратор возвращает тот же объект функции без обёртки."""

        # Arrange
        async def original_on_error(self, params, state, box, connections, error):
            pass

        # Act
        decorated = on_error(ValueError, description="Тест")(original_on_error)

        # Assert — тот же объект
        assert decorated is original_on_error


# ═════════════════════════════════════════════════════════════════════════════
# Ошибки типов исключений
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorExceptionTypeErrors:
    """Тесты ошибок при некорректных типах исключений."""

    def test_not_a_type(self) -> None:
        """Строка вместо типа → TypeError."""

        # Act & Assert — строка не является типом
        with pytest.raises(TypeError, match="должен быть типом Exception"):
            on_error("ValueError", description="Тест")  # type: ignore[arg-type]

    def test_not_exception_subclass(self) -> None:
        """Тип, не наследующий Exception → TypeError."""

        # Act & Assert — int не подкласс Exception
        with pytest.raises(TypeError, match="не является подклассом Exception"):
            on_error(int, description="Тест")  # type: ignore[arg-type]

    def test_empty_tuple(self) -> None:
        """Пустой кортеж типов → TypeError."""

        # Act & Assert
        with pytest.raises(TypeError, match="пустой кортеж"):
            on_error((), description="Тест")

    def test_tuple_with_non_type(self) -> None:
        """Кортеж с не-типом внутри → TypeError."""

        # Act & Assert
        with pytest.raises(TypeError, match="не является типом"):
            on_error((ValueError, "not_a_type"), description="Тест")  # type: ignore[arg-type]

    def test_tuple_with_non_exception(self) -> None:
        """Кортеж с типом, не наследующим Exception → TypeError."""

        # Act & Assert
        with pytest.raises(TypeError, match="не является подклассом Exception"):
            on_error((ValueError, int), description="Тест")  # type: ignore[arg-type]

    def test_integer_instead_of_type(self) -> None:
        """Число вместо типа → TypeError."""

        # Act & Assert
        with pytest.raises(TypeError, match="должен быть типом Exception"):
            on_error(42, description="Тест")  # type: ignore[arg-type]


# ═════════════════════════════════════════════════════════════════════════════
# Ошибки description
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorDescriptionErrors:
    """Тесты ошибок при некорректном description."""

    def test_description_not_string(self) -> None:
        """Число вместо строки description → TypeError."""

        # Act & Assert
        with pytest.raises(TypeError, match="description должен быть строкой"):
            on_error(ValueError, description=42)  # type: ignore[arg-type]

    def test_description_empty(self) -> None:
        """Пустая строка description → ValueError."""

        # Act & Assert
        with pytest.raises(ValueError, match="не может быть пустой"):
            on_error(ValueError, description="")

    def test_description_whitespace_only(self) -> None:
        """Строка из пробелов в description → ValueError."""

        # Act & Assert
        with pytest.raises(ValueError, match="не может быть пустой"):
            on_error(ValueError, description="   ")


# ═════════════════════════════════════════════════════════════════════════════
# Ошибки метода
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorMethodErrors:
    """Тесты ошибок при некорректном декорируемом методе."""

    def test_not_callable(self) -> None:
        """Применение к не-callable → TypeError."""

        # Act & Assert
        with pytest.raises(TypeError, match="только к методам"):
            on_error(ValueError, description="Тест")(42)

    def test_sync_method(self) -> None:
        """Синхронный метод → TypeError."""

        # Arrange — синхронная функция
        def sync_on_error(self, params, state, box, connections, error):
            pass

        # Act & Assert
        with pytest.raises(TypeError, match="асинхронным"):
            on_error(ValueError, description="Тест")(sync_on_error)

    def test_wrong_param_count_too_few(self) -> None:
        """Меньше 6 параметров → TypeError."""

        # Arrange — 5 параметров вместо 6
        async def short_on_error(self, params, state, box, connections):
            pass

        # Act & Assert
        with pytest.raises(TypeError, match="6 параметров"):
            on_error(ValueError, description="Тест")(short_on_error)

    def test_wrong_param_count_too_many(self) -> None:
        """Больше 6 параметров → TypeError."""

        # Arrange — 7 параметров
        async def long_on_error(self, params, state, box, connections, error, extra):
            pass

        # Act & Assert
        with pytest.raises(TypeError, match="6 параметров"):
            on_error(ValueError, description="Тест")(long_on_error)


# ═════════════════════════════════════════════════════════════════════════════
# Ошибки суффикса имени
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorNamingSuffix:
    """Тесты проверки суффикса '_on_error' в имени метода."""

    def test_missing_suffix(self) -> None:
        """Имя без суффикса '_on_error' → NamingSuffixError."""

        # Arrange — метод с правильной сигнатурой, но без суффикса
        async def handle_validation(self, params, state, box, connections, error):
            pass

        # Act & Assert
        with pytest.raises(NamingSuffixError, match="_on_error"):
            on_error(ValueError, description="Тест")(handle_validation)

    def test_wrong_suffix(self) -> None:
        """Имя с неправильным суффиксом → NamingSuffixError."""

        # Arrange — суффикс "_handler" вместо "_on_error"
        async def handle_validation_handler(self, params, state, box, connections, error):
            pass

        # Act & Assert
        with pytest.raises(NamingSuffixError, match="_on_error"):
            on_error(ValueError, description="Тест")(handle_validation_handler)

    def test_correct_suffix_passes(self) -> None:
        """Имя с правильным суффиксом → декоратор применяется без ошибок."""

        # Arrange & Act — суффикс "_on_error" корректен
        @on_error(ValueError, description="Тест суффикса")
        async def handle_validation_on_error(self, params, state, box, connections, error):
            pass

        # Assert — метаданные записаны
        assert hasattr(handle_validation_on_error, "_on_error_meta")
