# tests/context/test_context_requires_decorator.py
"""
Тесты декоратора @context_requires — запись контекстных зависимостей
в атрибут метода _required_context_keys.
"""

import pytest

from action_machine.context.context_requires_decorator import context_requires
from action_machine.context.ctx_constants import Ctx


class TestSingleKey:
    """Один ключ записывается как frozenset с одним элементом."""

    def test_single_constant_key(self) -> None:
        # Arrange — декоратор с одной константой Ctx
        @context_requires(Ctx.User.user_id)
        async def my_method(self, params, state, box, connections, ctx):
            pass

        # Act — читаем записанный атрибут
        keys = my_method._required_context_keys

        # Assert — frozenset с одним элементом
        assert keys == frozenset({"user.user_id"})

    def test_single_string_key(self) -> None:
        # Arrange — декоратор со строковым путём (кастомное поле)
        @context_requires("user.extra.billing_plan")
        async def my_method(self, params, state, box, connections, ctx):
            pass

        # Act
        keys = my_method._required_context_keys

        # Assert
        assert keys == frozenset({"user.extra.billing_plan"})


class TestMultipleKeys:
    """Несколько ключей записываются как frozenset с несколькими элементами."""

    def test_two_constants(self) -> None:
        # Arrange — декоратор с двумя константами
        @context_requires(Ctx.User.user_id, Ctx.User.roles)
        async def my_method(self, params, state, box, connections, ctx):
            pass

        # Act
        keys = my_method._required_context_keys

        # Assert — frozenset с двумя элементами
        assert keys == frozenset({"user.user_id", "user.roles"})

    def test_keys_from_different_components(self) -> None:
        # Arrange — ключи из разных компонентов контекста
        @context_requires(Ctx.User.user_id, Ctx.Request.trace_id, Ctx.Runtime.hostname)
        async def my_method(self, params, state, box, connections, ctx):
            pass

        # Act
        keys = my_method._required_context_keys

        # Assert — все три ключа в множестве
        assert keys == frozenset({"user.user_id", "request.trace_id", "runtime.hostname"})

    def test_mixed_constants_and_strings(self) -> None:
        # Arrange — смесь констант Ctx и строковых путей
        @context_requires(Ctx.User.user_id, "user.extra.billing_plan")
        async def my_method(self, params, state, box, connections, ctx):
            pass

        # Act
        keys = my_method._required_context_keys

        # Assert — оба ключа в множестве
        assert keys == frozenset({"user.user_id", "user.extra.billing_plan"})


class TestDuplicateKeys:
    """Дублирующиеся ключи схлопываются в frozenset."""

    def test_duplicate_keys_deduplicated(self) -> None:
        # Arrange — один и тот же ключ дважды
        @context_requires(Ctx.User.user_id, Ctx.User.user_id)
        async def my_method(self, params, state, box, connections, ctx):
            pass

        # Act
        keys = my_method._required_context_keys

        # Assert — frozenset автоматически убирает дубликаты
        assert keys == frozenset({"user.user_id"})
        assert len(keys) == 1


class TestReturnsFunctionUnchanged:
    """Декоратор возвращает исходную функцию без изменений."""

    def test_function_identity(self) -> None:
        # Arrange — исходная функция
        async def original(self, params, state, box, connections, ctx):
            return "result"

        # Act — применяем декоратор
        decorated = context_requires(Ctx.User.user_id)(original)

        # Assert — та же функция, не обёртка
        assert decorated is original

    def test_function_name_preserved(self) -> None:
        # Arrange / Act
        @context_requires(Ctx.User.user_id)
        async def my_named_method(self, params, state, box, connections, ctx):
            pass

        # Assert — имя метода не изменилось
        assert my_named_method.__name__ == "my_named_method"


class TestKeysType:
    """Записанный атрибут _required_context_keys имеет тип frozenset."""

    def test_type_is_frozenset(self) -> None:
        # Arrange / Act
        @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
        async def my_method(self, params, state, box, connections, ctx):
            pass

        # Assert — тип frozenset, не set и не list
        assert isinstance(my_method._required_context_keys, frozenset)


class TestInvalidNoKeys:
    """Пустой вызов @context_requires() — ValueError."""

    def test_no_keys_raises_value_error(self) -> None:
        # Arrange / Act / Assert — пустой вызов без аргументов
        with pytest.raises(ValueError, match="хотя бы один ключ"):
            @context_requires()
            async def my_method(self, params, state, box, connections, ctx):
                pass


class TestInvalidKeyType:
    """Нестроковый ключ — TypeError."""

    def test_int_key_raises_type_error(self) -> None:
        # Arrange / Act / Assert — целое число вместо строки
        with pytest.raises(TypeError, match="должен быть строкой"):
            @context_requires(42)  # type: ignore[arg-type]
            async def my_method(self, params, state, box, connections, ctx):
                pass

    def test_none_key_raises_type_error(self) -> None:
        # Arrange / Act / Assert — None вместо строки
        with pytest.raises(TypeError, match="должен быть строкой"):
            @context_requires(None)  # type: ignore[arg-type]
            async def my_method(self, params, state, box, connections, ctx):
                pass

    def test_list_key_raises_type_error(self) -> None:
        # Arrange / Act / Assert — список вместо строки
        with pytest.raises(TypeError, match="должен быть строкой"):
            @context_requires(["user.user_id"])  # type: ignore[arg-type]
            async def my_method(self, params, state, box, connections, ctx):
                pass


class TestInvalidEmptyKey:
    """Пустая строка в качестве ключа — ValueError."""

    def test_empty_string_raises_value_error(self) -> None:
        # Arrange / Act / Assert
        with pytest.raises(ValueError, match="не может быть пустой строкой"):
            @context_requires("")
            async def my_method(self, params, state, box, connections, ctx):
                pass

    def test_whitespace_only_raises_value_error(self) -> None:
        # Arrange / Act / Assert — строка из пробелов
        with pytest.raises(ValueError, match="не может быть пустой строкой"):
            @context_requires("   ")
            async def my_method(self, params, state, box, connections, ctx):
                pass

    def test_mixed_valid_and_empty_raises(self) -> None:
        # Arrange / Act / Assert — один валидный ключ, один пустой
        with pytest.raises(ValueError, match="не может быть пустой строкой"):
            @context_requires(Ctx.User.user_id, "")
            async def my_method(self, params, state, box, connections, ctx):
                pass


class TestInvalidTarget:
    """Декоратор применяется только к callable."""

    def test_non_callable_raises_type_error(self) -> None:
        # Arrange — строка вместо функции
        decorator = context_requires(Ctx.User.user_id)

        # Act / Assert
        with pytest.raises(TypeError, match="только к методам"):
            decorator("not a function")

    def test_int_target_raises_type_error(self) -> None:
        # Arrange — число вместо функции
        decorator = context_requires(Ctx.User.user_id)

        # Act / Assert
        with pytest.raises(TypeError, match="только к методам"):
            decorator(42)
