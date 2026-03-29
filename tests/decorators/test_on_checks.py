# tests/decorators/test_on_checks.py
"""
Тесты проверок декоратора @on.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ ИНВАРИАНТЫ
═══════════════════════════════════════════════════════════════════════════════

- Применение к async-методу с 4 параметрами (self, state, event, log) — успех.
- Несколько @on на одном методе — все подписки сохраняются.
- Применение к синхронному методу — TypeError.
- Применение к методу с менее чем 4 параметрами — TypeError.
- Применение к методу с более чем 4 параметрами — TypeError.
- Применение к не-callable объекту — TypeError.
- event_type не строка — TypeError.
- event_type пустая строка — ValueError.
- action_filter не строка — TypeError.
- Проверка сохранённых SubscriptionInfo после декорирования.
- Иммутабельность SubscriptionInfo (frozen=True).
"""

import pytest

from action_machine.plugins.decorators import SubscriptionInfo, on

# ─────────────────────────────────────────────────────────────────────────────
# Успешные сценарии
# ─────────────────────────────────────────────────────────────────────────────

class TestOnSuccess:
    """Проверка корректного применения @on к обработчикам с 4 параметрами."""

    def test_valid_async_method(self):
        """async-метод с 4 параметрами — подписка прикрепляется."""

        @on("global_finish", ".*")
        async def handler(self, state, event, log):
            return state

        assert hasattr(handler, '_on_subscriptions')
        assert len(handler._on_subscriptions) == 1
        sub = handler._on_subscriptions[0]
        assert isinstance(sub, SubscriptionInfo)
        assert sub.event_type == "global_finish"
        assert sub.action_filter == ".*"
        assert sub.ignore_exceptions is True

    def test_default_action_filter(self):
        """action_filter по умолчанию — '.*'."""

        @on("aspect_before")
        async def handler(self, state, event, log):
            return state

        sub = handler._on_subscriptions[0]
        assert sub.action_filter == ".*"

    def test_ignore_exceptions_false(self):
        """ignore_exceptions=False сохраняется."""

        @on("global_finish", ".*", ignore_exceptions=False)
        async def handler(self, state, event, log):
            return state

        sub = handler._on_subscriptions[0]
        assert sub.ignore_exceptions is False

    def test_custom_action_filter(self):
        """Кастомный action_filter сохраняется."""

        @on("aspect_after", "^CreateOrder.*$")
        async def handler(self, state, event, log):
            return state

        sub = handler._on_subscriptions[0]
        assert sub.action_filter == "^CreateOrder.*$"

    def test_does_not_change_function_name(self):
        """Декоратор не меняет имя функции."""

        @on("global_finish")
        async def my_handler(self, state, event, log):
            return state

        assert my_handler.__name__ == "my_handler"

    def test_function_remains_callable(self):
        """Декорированная функция остаётся вызываемой."""

        @on("global_finish")
        async def handler(self, state, event, log):
            return state

        assert callable(handler)

    def test_multiple_on_same_method(self):
        """Несколько @on на одном методе — все подписки сохраняются."""

        @on("global_start", ".*")
        @on("global_finish", ".*")
        @on("before:validate", "CreateOrder.*")
        async def handler(self, state, event, log):
            return state

        assert len(handler._on_subscriptions) == 3
        event_types = [sub.event_type for sub in handler._on_subscriptions]
        assert "global_start" in event_types
        assert "global_finish" in event_types
        assert "before:validate" in event_types


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: неправильная цель декоратора
# ─────────────────────────────────────────────────────────────────────────────

class TestOnTargetErrors:
    """Проверка ошибок при неправильном применении @on."""

    def test_sync_method_raises(self):
        """Синхронный метод — TypeError."""
        with pytest.raises(TypeError, match="должен быть асинхронным"):
            @on("global_finish")
            def handler(self, state, event, log):
                return state

    def test_one_param_raises(self):
        """Один параметр — TypeError."""
        with pytest.raises(TypeError, match="должен принимать 4 параметра"):
            @on("global_finish")
            async def handler(self):
                return {}

    def test_two_params_raises(self):
        """Два параметра — TypeError."""
        with pytest.raises(TypeError, match="должен принимать 4 параметра"):
            @on("global_finish")
            async def handler(self, state):
                return state

    def test_three_params_raises(self):
        """Три параметра (старая сигнатура без log) — TypeError."""
        with pytest.raises(TypeError, match="должен принимать 4 параметра"):
            @on("global_finish")
            async def handler(self, state, event):
                return state

    def test_five_params_raises(self):
        """Пять параметров — TypeError."""
        with pytest.raises(TypeError, match="должен принимать 4 параметра"):
            @on("global_finish")
            async def handler(self, state, event, log, extra):
                return state

    def test_not_callable_raises(self):
        """Не-callable объект — TypeError."""
        with pytest.raises(TypeError, match="только к методам"):
            on("global_finish")(42)

    def test_string_target_raises(self):
        """Строка вместо функции — TypeError."""
        with pytest.raises(TypeError, match="только к методам"):
            on("global_finish")("not a function")

    def test_none_target_raises(self):
        """None вместо функции — TypeError."""
        with pytest.raises(TypeError, match="только к методам"):
            on("global_finish")(None)


# ─────────────────────────────────────────────────────────────────────────────
# Ошибки: неправильные аргументы декоратора
# ─────────────────────────────────────────────────────────────────────────────

class TestOnArgumentErrors:
    """Проверка ошибок при передаче некорректных аргументов в @on."""

    def test_event_type_not_string_raises(self):
        """event_type не строка — TypeError."""
        with pytest.raises(TypeError, match="event_type должен быть строкой"):
            on(123)

    def test_event_type_none_raises(self):
        """event_type None — TypeError."""
        with pytest.raises(TypeError, match="event_type должен быть строкой"):
            on(None)

    def test_event_type_empty_raises(self):
        """event_type пустая строка — ValueError."""
        with pytest.raises(ValueError, match="не может быть пустой строкой"):
            on("")

    def test_event_type_whitespace_raises(self):
        """event_type из пробелов — ValueError."""
        with pytest.raises(ValueError, match="не может быть пустой строкой"):
            on("   ")

    def test_action_filter_not_string_raises(self):
        """action_filter не строка — TypeError."""
        with pytest.raises(TypeError, match="action_filter должен быть строкой"):
            on("global_finish", 123)

    def test_action_filter_none_raises(self):
        """action_filter None — TypeError."""
        with pytest.raises(TypeError, match="action_filter должен быть строкой"):
            on("global_finish", None)


# ─────────────────────────────────────────────────────────────────────────────
# Иммутабельность SubscriptionInfo
# ─────────────────────────────────────────────────────────────────────────────

class TestSubscriptionInfoImmutability:
    """Проверка, что SubscriptionInfo неизменяем (frozen=True)."""

    def test_cannot_modify_event_type(self):
        sub = SubscriptionInfo(event_type="global_finish", action_filter=".*")
        with pytest.raises(AttributeError):
            sub.event_type = "other"

    def test_cannot_modify_action_filter(self):
        sub = SubscriptionInfo(event_type="global_finish", action_filter=".*")
        with pytest.raises(AttributeError):
            sub.action_filter = "other"

    def test_cannot_modify_ignore_exceptions(self):
        sub = SubscriptionInfo(event_type="global_finish")
        with pytest.raises(AttributeError):
            sub.ignore_exceptions = False
