"""
Тесты для OnGateHost — миксина, который присоединяет OnGate к классу плагина.

Проверяем:
- Сбор подписок из декоратора @on
- Преобразование строковых regex в скомпилированные объекты
- Заморозку шлюза после сборки
- Удаление временного атрибута _on_subscriptions после сборки
- Отсутствие наследования подписок (каждый плагин определяет свои)
- Множественные подписки на одном методе
"""

import re

import pytest

from action_machine.Plugins.Decorators import on
from action_machine.Plugins.on_gate_host import OnGateHost


class TestOnGateHost:
    """Тесты для OnGateHost."""

    # ------------------------------------------------------------------
    # Сбор подписок
    # ------------------------------------------------------------------
    def test_subscriptions_are_collected(self):
        """
        Подписки, добавленные декоратором @on, регистрируются в шлюзе.
        """
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