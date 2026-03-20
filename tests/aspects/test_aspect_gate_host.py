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
            pass
        action = MyAction()
        # До обращения свойство не создано
        assert action._aspects_gate is None
        gate = action.aspects
        assert gate is not None
        assert action._aspects_gate is gate

    def test_get_aspects_empty(self):
        class MyAction(AspectGateHost):
            pass
        action = MyAction()
        regular, summary = action.get_aspects()
        assert regular == []
        assert summary is None

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
        class MyAction(AspectGateHost):
            @regular_aspect("only")
            async def only(self): pass

        with pytest.raises(TypeError, match="does not have a summary aspect"):
            MyAction()  # создание класса вызовет ошибку в __init_subclass__

    def test_summary_from_parent_satisfies(self):
        class Parent(AspectGateHost):
            @summary_aspect("parent_summary")
            async def parent_summary(self): pass

        class Child(Parent):
            @regular_aspect("child")
            async def child_aspect(self): pass

        # Ошибки быть не должно
        child = Child()
        regular, summary = child.get_aspects()
        assert summary is not None
        assert summary[0].__name__ == "parent_summary"

    def test_duplicate_summary_in_child_raises(self):
        class Parent(AspectGateHost):
            @summary_aspect("parent_summary")
            async def parent_summary(self): pass

        with pytest.raises(TypeError, match="Only one summary aspect can be registered"):
            class Child(Parent):
                @summary_aspect("child_summary")
                async def child_summary(self): pass

    def test_aspects_are_registered_only_once(self):
        class MyAction(AspectGateHost):
            @regular_aspect("test")
            async def test(self): pass
            @summary_aspect("summary")
            async def summ(self): pass

        # После создания класса временные атрибуты должны быть удалены
        assert not hasattr(MyAction.test, '_new_aspect_meta')
        assert not hasattr(MyAction.summ, '_new_aspect_meta')