# tests/intents/compensate/test_compensate_decorator.py
"""
Тесты декоратора @compensate — проверка валидаций при определении класса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что декоратор @compensate корректно валидирует аргументы,
сигнатуру метода и суффикс имени при определении класса (import-time).
Все тесты — синхронные, не требуют запуска машины.

═══════════════════════════════════════════════════════════════════════════════
СТРУКТУРА
═══════════════════════════════════════════════════════════════════════════════

TestCompensateDecoratorSuccess      — корректные случаи
TestCompensateTargetErrors          — ошибки target_aspect_name
TestCompensateDescriptionErrors     — ошибки description
TestCompensateMethodErrors          — ошибки метода (синхронность, сигнатура)
TestCompensateNamingSuffix          — ошибки суффикса имени метода
"""

from __future__ import annotations

import pytest

from action_machine.intents.compensate import compensate
from action_machine.intents.context import context_requires

# ═════════════════════════════════════════════════════════════════════════════
# TestCompensateDecoratorSuccess — корректные случаи
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensateDecoratorSuccess:
    """Проверяет, что декоратор @compensate правильно работает с корректными данными."""

    def test_correct_decorator_with_7_params(self) -> None:
        """
        Корректный декоратор с 7 параметрами (без @context_requires).
        """

        class Action:
            @compensate("some_aspect", "Описание компенсатора")
            async def rollback_compensate(self, params, state_before, state_after,
                                          box, connections, error):
                pass

        method = Action.rollback_compensate
        assert hasattr(method, "_compensate_meta")
        meta = method._compensate_meta
        assert meta["target_aspect_name"] == "some_aspect"
        assert meta["description"] == "Описание компенсатора"

    def test_correct_decorator_with_8_params_and_context_requires(self) -> None:
        """
        Корректный декоратор с 8 параметрами (с @context_requires).
        """

        class Action:
            @compensate("some_aspect", "Описание с контекстом")
            @context_requires("user.user_id")
            async def rollback_with_context_compensate(self, params, state_before, state_after,
                                                       box, connections, error, ctx):
                pass

        method = Action.rollback_with_context_compensate
        assert hasattr(method, "_compensate_meta")
        meta = method._compensate_meta
        assert meta["target_aspect_name"] == "some_aspect"
        assert meta["description"] == "Описание с контекстом"
        assert hasattr(method, "_required_context_keys")
        assert method._required_context_keys == {"user.user_id"}

    def test_decorator_returns_same_function(self) -> None:
        """
        Декоратор возвращает тот же объект функции (не обёртку).
        """

        async def rollback_compensate(self, params, state_before, state_after,
                                      box, connections, error):
            pass

        decorated = compensate("some_aspect", "Описание")(rollback_compensate)
        assert decorated is rollback_compensate


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensateTargetErrors — ошибки target_aspect_name
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensateTargetErrors:
    """Проверяет валидацию параметра target_aspect_name."""

    def test_target_aspect_name_not_string(self) -> None:
        """target_aspect_name не строка → TypeError."""
        with pytest.raises(TypeError, match="target_aspect_name должен быть строкой"):

            @compensate(123, "Описание")
            async def rollback_compensate(self, params, state_before, state_after,
                                          box, connections, error):
                pass

    def test_target_aspect_name_empty_string(self) -> None:
        """target_aspect_name пустая строка → ValueError."""
        with pytest.raises(ValueError, match="target_aspect_name не может быть пустой строкой"):

            @compensate("", "Описание")
            async def rollback_compensate(self, params, state_before, state_after,
                                          box, connections, error):
                pass

    def test_target_aspect_name_whitespace_only(self) -> None:
        """target_aspect_name из пробелов → ValueError."""
        with pytest.raises(ValueError, match="target_aspect_name не может быть пустой строкой"):

            @compensate("   ", "Описание")
            async def rollback_compensate(self, params, state_before, state_after,
                                          box, connections, error):
                pass


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensateDescriptionErrors — ошибки description
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensateDescriptionErrors:
    """Проверяет валидацию параметра description."""

    def test_description_not_string(self) -> None:
        """description не строка → TypeError."""
        with pytest.raises(TypeError, match="description должен быть строкой"):

            @compensate("some_aspect", 123)
            async def rollback_compensate(self, params, state_before, state_after,
                                          box, connections, error):
                pass

    def test_description_empty_string(self) -> None:
        """description пустая строка → ValueError."""
        with pytest.raises(ValueError, match="description не может быть пустой строкой"):

            @compensate("some_aspect", "")
            async def rollback_compensate(self, params, state_before, state_after,
                                          box, connections, error):
                pass

    def test_description_whitespace_only(self) -> None:
        """description из пробелов → ValueError."""
        with pytest.raises(ValueError, match="description не может быть пустой строкой"):

            @compensate("some_aspect", "   ")
            async def rollback_compensate(self, params, state_before, state_after,
                                          box, connections, error):
                pass


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensateMethodErrors — ошибки метода
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensateMethodErrors:
    """Проверяет валидацию декорируемого метода."""

    def test_sync_method(self) -> None:
        """Синхронный метод → TypeError с сообщением о необходимости async def."""
        with pytest.raises(TypeError, match="должен быть корутиной"):

            @compensate("some_aspect", "Описание")
            def sync_compensate(self, params, state_before, state_after,
                                box, connections, error):
                pass

    def test_too_few_parameters_without_context(self) -> None:
        """Менее 7 параметров без @context_requires → TypeError."""
        with pytest.raises(TypeError, match="должен иметь 7 параметров"):

            @compensate("some_aspect", "Описание")
            async def too_few_params_compensate(self, params, state_before, state_after,
                                                box, connections):
                pass

    def test_too_many_parameters_without_context(self) -> None:
        """Более 7 параметров без @context_requires → TypeError."""
        with pytest.raises(TypeError, match="должен иметь 7 параметров"):

            @compensate("some_aspect", "Описание")
            async def too_many_params_compensate(self, params, state_before, state_after,
                                                 box, connections, error, extra):
                pass

    def test_too_few_parameters_with_context(self) -> None:
        """Менее 8 параметров с @context_requires → TypeError."""
        with pytest.raises(TypeError, match="должен иметь 8 параметров"):

            @compensate("some_aspect", "Описание")
            @context_requires("user.user_id")
            async def too_few_with_ctx_compensate(self, params, state_before, state_after,
                                                  box, connections, error):
                pass

    def test_too_many_parameters_with_context(self) -> None:
        """Более 8 параметров с @context_requires → TypeError."""
        with pytest.raises(TypeError, match="должен иметь 8 параметров"):

            @compensate("some_aspect", "Описание")
            @context_requires("user.user_id")
            async def too_many_with_ctx_compensate(self, params, state_before, state_after,
                                                   box, connections, error, ctx, extra):
                pass


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensateNamingSuffix — ошибки суффикса имени метода
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensateNamingSuffix:
    """Проверяет, что имя метода-компенсатора должно заканчиваться на '_compensate'."""

    def test_method_without_compensate_suffix(self) -> None:
        """Имя метода не заканчивается на '_compensate' → ValueError."""
        with pytest.raises(ValueError, match="должно заканчиваться на '_compensate'"):

            @compensate("some_aspect", "Описание")
            async def rollback_wrong(self, params, state_before, state_after,
                                     box, connections, error):
                pass

    def test_method_with_wrong_suffix(self) -> None:
        """Имя метода с неправильным суффиксом → ValueError."""
        with pytest.raises(ValueError, match="должно заканчиваться на '_compensate'"):

            @compensate("some_aspect", "Описание")
            async def rollback_rollback(self, params, state_before, state_after,
                                        box, connections, error):
                pass

    def test_method_with_correct_suffix(self) -> None:
        """Имя метода с суффиксом '_compensate' — успех."""
        class Action:
            @compensate("some_aspect", "Описание")
            async def rollback_compensate(self, params, state_before, state_after,
                                          box, connections, error):
                pass

        assert hasattr(Action.rollback_compensate, "_compensate_meta")
