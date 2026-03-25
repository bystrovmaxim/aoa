"""
Тесты для OnGate — шлюза управления подписками плагинов (декоратор @on).

Проверяем:
- Регистрацию подписок (Subscription)
- Получение обработчиков по событию и имени класса (get_handlers)
- Получение всех подписок (get_all_subscriptions, get_components)
- Удаление подписок (unregister)
- Заморозку шлюза (freeze)
- Обработку ошибок (регистрация/удаление после заморозки)
"""

import re

import pytest

from action_machine.Plugins.on_gate import OnGate, Subscription


# ----------------------------------------------------------------------
# Тестовые методы-обработчики
# ----------------------------------------------------------------------
async def handler1(state, event):
    return state


async def handler2(state, event):
    return state


async def handler3(state, event):
    return state


# ======================================================================
# Тесты для OnGate
# ======================================================================

class TestOnGate:
    """Тесты для OnGate."""

    # ------------------------------------------------------------------
    # Регистрация
    # ------------------------------------------------------------------
    def test_register(self):
        """Регистрация подписки."""
        gate = OnGate()
        sub = Subscription(
            method=handler1,
            event_regex=re.compile("test_event"),
            class_regex=re.compile(".*"),
            ignore_exceptions=False,
        )

        result = gate.register(sub)

        assert result is sub
        assert gate.get_components() == [sub]
        assert gate.get_all_subscriptions() == [sub]

    def test_register_with_string_regex(self):
        """
        Регистрация подписки, где regex переданы как скомпилированные объекты.
        В тесте используем уже скомпилированные.
        """
        gate = OnGate()
        sub = Subscription(
            method=handler1,
            event_regex=re.compile("test_.*"),
            class_regex=re.compile(".*Action"),
            ignore_exceptions=True,
        )
        gate.register(sub)
        assert gate.get_components() == [sub]

    def test_register_multiple_subscriptions(self):
        """Регистрация нескольких подписок (порядок сохраняется)."""
        gate = OnGate()
        sub1 = Subscription(handler1, re.compile("event1"), re.compile(".*"), False)
        sub2 = Subscription(handler2, re.compile("event2"), re.compile(".*"), True)

        gate.register(sub1)
        gate.register(sub2)

        assert gate.get_components() == [sub1, sub2]

    # ------------------------------------------------------------------
    # Получение обработчиков
    # ------------------------------------------------------------------
    def test_get_handlers_matches_event_and_class(self):
        """get_handlers возвращает обработчики, чьи regex совпадают."""
        gate = OnGate()
        sub1 = Subscription(
            handler1,
            event_regex=re.compile("global_start"),
            class_regex=re.compile(".*OrderAction"),
            ignore_exceptions=False,
        )
        sub2 = Subscription(
            handler2,
            event_regex=re.compile("global_start"),
            class_regex=re.compile(".*PaymentAction"),
            ignore_exceptions=True,
        )
        sub3 = Subscription(
            handler3,
            event_regex=re.compile("global_finish"),
            class_regex=re.compile(".*"),
            ignore_exceptions=False,
        )

        gate.register(sub1)
        gate.register(sub2)
        gate.register(sub3)

        handlers = gate.get_handlers("global_start", "myapp.OrderAction")
        assert len(handlers) == 1
        assert handlers[0] == (handler1, False)

        handlers = gate.get_handlers("global_start", "myapp.PaymentAction")
        assert len(handlers) == 1
        assert handlers[0] == (handler2, True)

        handlers = gate.get_handlers("global_start", "myapp.OtherAction")
        assert handlers == []

    def test_get_handlers_multiple_matches(self):
        """Если несколько подписок совпадают, возвращаются все в порядке регистрации."""
        gate = OnGate()
        sub1 = Subscription(handler1, re.compile("event.*"), re.compile(".*"), False)
        sub2 = Subscription(handler2, re.compile("event.*"), re.compile(".*"), True)
        sub3 = Subscription(handler3, re.compile("other"), re.compile(".*"), False)

        gate.register(sub1)
        gate.register(sub2)
        gate.register(sub3)

        handlers = gate.get_handlers("event_start", "MyAction")
        assert handlers == [(handler1, False), (handler2, True)]

    def test_get_handlers_empty_if_no_match(self):
        """Если нет подходящих подписок, возвращается пустой список."""
        gate = OnGate()
        sub = Subscription(handler1, re.compile("event"), re.compile(".*"), False)
        gate.register(sub)

        handlers = gate.get_handlers("other_event", "MyAction")
        assert handlers == []

    # ------------------------------------------------------------------
    # Получение компонентов
    # ------------------------------------------------------------------
    def test_get_components_returns_copy(self):
        """get_components возвращает копию списка, внешние изменения не влияют на шлюз."""
        gate = OnGate()
        sub = Subscription(handler1, re.compile(".*"), re.compile(".*"), False)
        gate.register(sub)

        components = gate.get_components()
        components.append(Subscription(handler2, re.compile(".*"), re.compile(".*"), False))

        assert gate.get_components() == [sub]

    def test_get_all_subscriptions_alias(self):
        """get_all_subscriptions — синоним get_components."""
        gate = OnGate()
        sub = Subscription(handler1, re.compile(".*"), re.compile(".*"), False)
        gate.register(sub)

        assert gate.get_all_subscriptions() == gate.get_components()

    # ------------------------------------------------------------------
    # Удаление
    # ------------------------------------------------------------------
    def test_unregister(self):
        """Удаление подписки по ссылке."""
        gate = OnGate()
        sub1 = Subscription(handler1, re.compile(".*"), re.compile(".*"), False)
        sub2 = Subscription(handler2, re.compile(".*"), re.compile(".*"), False)

        gate.register(sub1)
        gate.register(sub2)
        gate.unregister(sub1)

        assert gate.get_components() == [sub2]

    def test_unregister_nonexistent_ignored(self):
        """Удаление незарегистрированной подписки не вызывает ошибку."""
        gate = OnGate()
        sub = Subscription(handler1, re.compile(".*"), re.compile(".*"), False)
        gate.unregister(sub)  # не падает

    def test_unregister_wrong_instance_does_nothing(self):
        """Если передан другой объект с теми же атрибутами, удаление не происходит."""
        gate = OnGate()
        original = Subscription(handler1, re.compile(".*"), re.compile(".*"), False)
        other = Subscription(handler1, re.compile(".*"), re.compile(".*"), False)

        gate.register(original)
        gate.unregister(other)

        assert gate.get_components() == [original]

    # ------------------------------------------------------------------
    # Заморозка
    # ------------------------------------------------------------------
    def test_freeze_disables_register(self):
        """После freeze() регистрация запрещена."""
        gate = OnGate()
        gate.freeze()

        sub = Subscription(handler1, re.compile(".*"), re.compile(".*"), False)
        with pytest.raises(RuntimeError, match="OnGate is frozen"):
            gate.register(sub)

    def test_freeze_disables_unregister(self):
        """После freeze() удаление запрещено."""
        gate = OnGate()
        sub = Subscription(handler1, re.compile(".*"), re.compile(".*"), False)
        gate.register(sub)
        gate.freeze()

        with pytest.raises(RuntimeError, match="OnGate is frozen"):
            gate.unregister(sub)

    def test_freeze_idempotent(self):
        """Повторный вызов freeze() не вызывает ошибок."""
        gate = OnGate()
        gate.freeze()
        gate.freeze()  # не падает

    # ------------------------------------------------------------------
    # Методы после заморозки
    # ------------------------------------------------------------------
    def test_get_methods_work_after_freeze(self):
        """Методы получения работают после заморозки (только чтение)."""
        gate = OnGate()
        sub = Subscription(handler1, re.compile("event"), re.compile(".*"), False)
        gate.register(sub)
        gate.freeze()

        assert gate.get_handlers("event", "MyAction") == [(handler1, False)]
        assert gate.get_components() == [sub]