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
        assert action._instance_gate is None
        gate = action.aspects
        assert gate is not None
        assert action._instance_gate is None  # всё ещё None, используется классовый шлюз
        assert gate is MyAction._class_gate

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

            MyAction()  # создание экземпляра вызывает проверку в __init__

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


class TestAspectGateHostCopyOnWrite:
    """Тесты для copy-on-write в AspectGateHost."""

    def test_instances_share_gate_by_default(self):
        class MyAction(AspectGateHost):
            @regular_aspect("r1")
            async def r1(self): pass
            @regular_aspect("r2")
            async def r2(self): pass
            @summary_aspect("s")
            async def s(self): pass

        a1 = MyAction()
        a2 = MyAction()

        # Оба используют один и тот же объект шлюза (классовый)
        assert a1.aspects is a2.aspects
        assert a1.aspects is MyAction._class_gate

    def test_add_regular_aspect_creates_copy(self):
        class MyAction(AspectGateHost):
            @regular_aspect("r1")
            async def r1(self): pass
            @summary_aspect("s")
            async def s(self): pass

        a1 = MyAction()
        a2 = MyAction()

        original_gate = MyAction._class_gate

        # Добавляем аспект к a1
        async def new_regular(): pass
        a1.add_regular_aspect(new_regular, "new")

        # У a1 теперь свой шлюз, у a2 – общий
        assert a1.aspects is not original_gate
        assert a2.aspects is original_gate

        # Проверяем, что аспект добавился только у a1
        regular1, _ = a1.get_aspects()
        regular2, _ = a2.get_aspects()
        assert len(regular1) == 2  # r1 + new
        assert len(regular2) == 1  # только r1

        # Проверяем, что оригинальный шлюз не изменился
        assert len(original_gate.get_regular()) == 1

    def test_remove_regular_aspect_creates_copy(self):
        class MyAction(AspectGateHost):
            @regular_aspect("r1")
            async def r1(self): pass
            @summary_aspect("s")
            async def s(self): pass

        a1 = MyAction()
        a2 = MyAction()

        original_gate = MyAction._class_gate

        # Удаляем аспект у a1 – передаём классовый метод, а не bound
        a1.remove_regular_aspect(MyAction.r1)

        assert a1.aspects is not original_gate
        assert a2.aspects is original_gate

        regular1, _ = a1.get_aspects()
        regular2, _ = a2.get_aspects()
        assert len(regular1) == 0
        assert len(regular2) == 1

        assert len(original_gate.get_regular()) == 1

    def test_set_summary_aspect_creates_copy(self):
        class MyAction(AspectGateHost):
            @regular_aspect("r1")
            async def r1(self): pass
            @summary_aspect("s1")
            async def s1(self): pass

        a1 = MyAction()
        a2 = MyAction()

        async def new_summary(): pass
        a1.set_summary_aspect(new_summary, "new summary")

        assert a1.aspects is not a2.aspects
        _, summary1 = a1.get_aspects()
        _, summary2 = a2.get_aspects()
        assert summary1[0] is new_summary
        # summary2[0] должен быть исходным summary-аспектом класса
        assert summary2[0] is MyAction.s1

    def test_remove_summary_aspect_creates_copy(self):
        class MyAction(AspectGateHost):
            @regular_aspect("r1")
            async def r1(self): pass
            @summary_aspect("s1")
            async def s1(self): pass

        a1 = MyAction()
        a2 = MyAction()

        a1.remove_summary_aspect()

        _, summary1 = a1.get_aspects()
        _, summary2 = a2.get_aspects()
        assert summary1 is None
        assert summary2 is not None

    def test_multiple_changes_same_instance(self):
        class MyAction(AspectGateHost):
            @regular_aspect("r1")
            async def r1(self): pass
            @summary_aspect("s")
            async def s(self): pass

        a = MyAction()

        # Первое изменение создаёт копию
        async def r2(): pass
        a.add_regular_aspect(r2, "r2")
        gate1 = a._instance_gate

        # Второе изменение использует ту же копию, новую не создаёт
        a.remove_regular_aspect(MyAction.r1)
        assert a._instance_gate is gate1

        regular, _ = a.get_aspects()
        assert len(regular) == 1
        assert regular[0][0] is r2