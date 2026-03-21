# tests/plugins/test_on_gate.py
"""
Тесты для OnGate — шлюза управления подписками плагинов (декоратор @on).

Проверяем:
- Регистрацию подписок (Subscription)
- Получение обработчиков по событию и имени класса (get_handlers)
- Получение всех подписок (get_all_subscriptions, get_components)
- Удаление подписок (unregister)
- Заморозку шлюза (freeze)
- Обработку ошибок (регистрация/удаление после заморозки)
- Сбор подписок через OnGateHost (миксин)

Изменения:
- Тесты переписаны с использованием декоратора @on вместо ручного присвоения
  атрибута _on_subscriptions после создания класса. Это гарантирует,
  что подписки будут зарегистрированы в __init_subclass__ во время
  определения класса, а не после.
- Добавлен импорт on из action_machine.Plugins.Decorators.
- Обновлены комментарии.
"""

import re

import pytest

from action_machine.Plugins.Decorators import on
from action_machine.Plugins.on_gate import OnGate, Subscription
from action_machine.Plugins.on_gate_host import OnGateHost


# ----------------------------------------------------------------------
# Тестовые методы-обработчики (для прямого тестирования OnGate)
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
        Регистрация подписки, где regex переданы как строки.
        OnGateHost преобразует их в скомпилированные объекты перед регистрацией.
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


# ======================================================================
# Тесты для OnGateHost (миксин, который собирает подписки)
# ======================================================================

class TestOnGateHost:
    """
    Тесты для OnGateHost — миксина, который присоединяет OnGate к классу плагина.
    Проверяем:
    - Сбор подписок из декоратора @on
    - Заморозку шлюза после сборки
    - Отсутствие мутации родительских данных при наследовании
    """

    def test_subscriptions_are_collected(self):
        """Подписки, добавленные декоратором @on, регистрируются в шлюзе."""
        class MyPlugin(OnGateHost):
            @on("event1", ".*", ignore_exceptions=True)
            async def handler1(self, state, event):
                return state

            @on("event2", ".*OrderAction", ignore_exceptions=False)
            async def handler2(self, state, event):
                return state

        gate = MyPlugin.get_on_gate()
        subs = gate.get_components()
        assert len(subs) == 2

        # Проверяем первую подписку
        sub1 = subs[0]
        assert sub1.method is MyPlugin.handler1
        assert isinstance(sub1.event_regex, re.Pattern)
        assert sub1.event_regex.pattern == "event1"
        assert isinstance(sub1.class_regex, re.Pattern)
        assert sub1.class_regex.pattern == ".*"
        assert sub1.ignore_exceptions is True

        # Вторая подписка
        sub2 = subs[1]
        assert sub2.method is MyPlugin.handler2
        assert sub2.event_regex.pattern == "event2"
        assert sub2.class_regex.pattern == ".*OrderAction"
        assert sub2.ignore_exceptions is False

    def test_subscriptions_with_string_regex_are_compiled(self):
        """Строковые регулярные выражения в декораторе компилируются в re.Pattern."""
        class MyPlugin(OnGateHost):
            @on("test_event", "myapp\\.actions\\..*", ignore_exceptions=True)
            async def handler(self, state, event):
                return state

        gate = MyPlugin.get_on_gate()
        sub = gate.get_components()[0]

        assert isinstance(sub.event_regex, re.Pattern)
        assert isinstance(sub.class_regex, re.Pattern)
        assert sub.event_regex.pattern == "test_event"
        assert sub.class_regex.pattern == "myapp\\.actions\\..*"

    def test_temporary_attribute_removed_after_collection(self):
        """После сборки атрибут _on_subscriptions удаляется из методов."""
        class MyPlugin(OnGateHost):
            @on("event", ".*", ignore_exceptions=False)
            async def handler(self, state, event):
                return state

        # После создания класса атрибут должен быть удалён
        assert not hasattr(MyPlugin.handler, '_on_subscriptions')

    def test_inheritance_does_not_share_subscriptions(self):
        """
        Подписки не наследуются. Каждый класс плагина получает свой шлюз
        со своими подписками.
        """
        class Parent(OnGateHost):
            @on("parent_event", ".*", ignore_exceptions=False)
            async def parent_handler(self, state, event):
                return state

        class Child(Parent):
            @on("child_event", ".*", ignore_exceptions=True)
            async def child_handler(self, state, event):
                return state

        parent_gate = Parent.get_on_gate()
        child_gate = Child.get_on_gate()

        # Гейты разные
        assert parent_gate is not child_gate

        # У родителя только parent_handler
        parent_handlers = parent_gate.get_handlers("parent_event", "AnyAction")
        assert len(parent_handlers) == 1
        assert parent_handlers[0][0] is Parent.parent_handler
        assert parent_handlers[0][1] is False

        # У ребёнка только child_handler
        child_handlers = child_gate.get_handlers("child_event", "AnyAction")
        assert len(child_handlers) == 1
        assert child_handlers[0][0] is Child.child_handler
        assert child_handlers[0][1] is True

        # У родителя нет child_handler
        assert parent_gate.get_handlers("child_event", "AnyAction") == []
        # У ребёнка нет parent_handler
        assert child_gate.get_handlers("parent_event", "AnyAction") == []

    def test_multiple_subscriptions_on_same_method(self):
        """Один метод может иметь несколько подписок (разные события/классы)."""
        class MyPlugin(OnGateHost):
            @on("event1", ".*", ignore_exceptions=False)
            @on("event2", ".*Action", ignore_exceptions=True)
            @on("global.*", "myapp\\..*", ignore_exceptions=False)
            async def handler(self, state, event):
                return state

        gate = MyPlugin.get_on_gate()
        subs = gate.get_components()
        assert len(subs) == 3

        # Проверяем, что все три подписки привязаны к одному методу
        for sub in subs:
            assert sub.method is MyPlugin.handler

        # Проверяем, что можно получить обработчики для каждого события
        handlers_event1 = gate.get_handlers("event1", "AnyClass")
        assert len(handlers_event1) == 1
        assert handlers_event1[0][0] is MyPlugin.handler
        assert handlers_event1[0][1] is False

        handlers_event2 = gate.get_handlers("event2", "MyAction")
        assert len(handlers_event2) == 1
        assert handlers_event2[0][0] is MyPlugin.handler
        assert handlers_event2[0][1] is True

        handlers_global = gate.get_handlers("global_start", "myapp.SomeAction")
        assert len(handlers_global) == 1
        assert handlers_global[0][0] is MyPlugin.handler
        assert handlers_global[0][1] is False