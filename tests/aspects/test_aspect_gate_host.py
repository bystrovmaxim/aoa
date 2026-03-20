# tests/aspects/test_aspect_gate_host.py
"""
Тесты для AspectGateHost — хоста шлюза аспектов.
"""

import pytest

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect


class TestAspectGateHost:
    def test_aspects_property_lazy_creation(self):
        class MyAction(AspectGateHost):
            @summary_aspect("test")
            async def summ(self): pass

        action = MyAction()
        assert action._aspects_gate is None
        gate = action.aspects
        assert gate is not None
        assert action._aspects_gate is gate

    def test_get_aspects_empty(self):
        class MyAction(AspectGateHost):
            @summary_aspect("test")
            async def summ(self): pass

        action = MyAction()
        regular, summary = action.get_aspects()
        assert regular == []
        assert summary is not None
        assert summary[0].__name__ == "summ"

    def test_get_aspects_with_aspects(self):
        class MyAction(AspectGateHost):
            @regular_aspect("first")
            async def first(self): pass
            @regular_aspect("second")
            async def second(self): pass
            @summary_aspect("summary")
            async def summ(self): pass

        action = MyAction()
        regular, summary = action.get_aspects()
        assert len(regular) == 2
        assert regular[0][0].__name__ == "first"
        assert regular[0][1] == "first"
        assert regular[1][0].__name__ == "second"
        assert regular[1][1] == "second"
        assert summary is not None
        assert summary[0].__name__ == "summ"
        assert summary[1] == "summary"

    def test_missing_summary_raises(self):
        with pytest.raises(TypeError, match="does not have a summary aspect"):
            class MyAction(AspectGateHost):
                @regular_aspect("only")
                async def only(self): pass

            # Создание экземпляра вызывает проверку в __init__
            MyAction()

    def test_child_must_have_own_summary(self):
        """Дочерний класс не наследует summary-аспект от родителя."""
        class Parent(AspectGateHost):
            @summary_aspect("parent_summary")
            async def parent_summary(self): pass

        with pytest.raises(TypeError, match="does not have a summary aspect"):
            class Child(Parent):
                @regular_aspect("child")
                async def child_aspect(self): pass

            Child()

    def test_duplicate_summary_in_single_class_raises(self):
        """В одном классе нельзя определить два summary-аспекта."""
        with pytest.raises(TypeError, match="Only one summary aspect can be registered"):
            class MyAction(AspectGateHost):
                @summary_aspect("first")
                async def summ1(self): pass
                @summary_aspect("second")
                async def summ2(self): pass

    def test_aspects_are_registered_only_once(self):
        class MyAction(AspectGateHost):
            @regular_aspect("test")
            async def test(self): pass
            @summary_aspect("summary")
            async def summ(self): pass

        assert not hasattr(MyAction.test, '_new_aspect_meta')
        assert not hasattr(MyAction.summ, '_new_aspect_meta')