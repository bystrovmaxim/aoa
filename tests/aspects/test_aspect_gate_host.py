# tests/aspects/test_aspect_gate_host.py
"""
Tests for AspectGateHost — the host for aspect gate.

Checks:
- Aspect registration via decorators
- Copy-on-write behavior for per-instance aspect changes

Изменения (этап 1):
- Во всех аспектах, определённых в тестах, заменены сигнатуры:
  параметры deps и log заменены на box: ToolsBox.
- Импортирован ToolsBox.
- Обновлены комментарии.
"""

import pytest

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect


class TestAspectGateHost:
    def test_aspects_property_lazy_creation(self):
        class MyAction(AspectGateHost):
            @summary_aspect("test")
            async def summ(self, params, state, box, connections):
                pass

        action = MyAction()
        assert action._instance_gate is None
        gate = action.aspects
        assert gate is not None
        assert action._instance_gate is None  # still None, uses class gate
        assert gate is MyAction._class_gate

    def test_get_aspects_empty(self):
        class MyAction(AspectGateHost):
            @summary_aspect("test")
            async def summ(self, params, state, box, connections):
                pass

        action = MyAction()
        regular, summary = action.get_aspects()
        assert regular == []
        assert summary is not None
        assert summary[0].__name__ == "summ"

    def test_get_aspects_with_aspects(self):
        class MyAction(AspectGateHost):
            @regular_aspect("first")
            async def first(self, params, state, box, connections):
                pass

            @regular_aspect("second")
            async def second(self, params, state, box, connections):
                pass

            @summary_aspect("summary")
            async def summ(self, params, state, box, connections):
                pass

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
                async def only(self, params, state, box, connections):
                    pass

            MyAction()  # instance creation triggers check in __init__

    def test_child_must_have_own_summary(self):
        """Child class does not inherit summary aspect from parent."""
        class Parent(AspectGateHost):
            @summary_aspect("parent_summary")
            async def parent_summary(self, params, state, box, connections):
                pass

        with pytest.raises(TypeError, match="does not have a summary aspect"):
            class Child(Parent):
                @regular_aspect("child")
                async def child_aspect(self, params, state, box, connections):
                    pass

            Child()

    def test_duplicate_summary_in_single_class_raises(self):
        """Cannot define two summary aspects in one class."""
        with pytest.raises(TypeError, match="Only one summary aspect can be registered"):
            class MyAction(AspectGateHost):
                @summary_aspect("first")
                async def summ1(self, params, state, box, connections):
                    pass

                @summary_aspect("second")
                async def summ2(self, params, state, box, connections):
                    pass

    def test_aspects_are_registered_only_once(self):
        class MyAction(AspectGateHost):
            @regular_aspect("test")
            async def test(self, params, state, box, connections):
                pass

            @summary_aspect("summary")
            async def summ(self, params, state, box, connections):
                pass

        assert not hasattr(MyAction.test, '_new_aspect_meta')
        assert not hasattr(MyAction.summ, '_new_aspect_meta')


class TestAspectGateHostCopyOnWrite:
    """Tests for copy-on-write in AspectGateHost."""

    def test_instances_share_gate_by_default(self):
        class MyAction(AspectGateHost):
            @regular_aspect("r1")
            async def r1(self, params, state, box, connections):
                pass

            @regular_aspect("r2")
            async def r2(self, params, state, box, connections):
                pass

            @summary_aspect("s")
            async def s(self, params, state, box, connections):
                pass

        a1 = MyAction()
        a2 = MyAction()

        # Both use the same gate object (class gate)
        assert a1.aspects is a2.aspects
        assert a1.aspects is MyAction._class_gate

    def test_add_regular_aspect_creates_copy(self):
        class MyAction(AspectGateHost):
            @regular_aspect("r1")
            async def r1(self, params, state, box, connections):
                pass

            @summary_aspect("s")
            async def s(self, params, state, box, connections):
                pass

        a1 = MyAction()
        a2 = MyAction()

        original_gate = MyAction._class_gate

        # Add aspect to a1
        async def new_regular(params, state, box, connections):
            pass

        a1.add_regular_aspect(new_regular, "new")

        # a1 now has its own gate, a2 still uses class gate
        assert a1.aspects is not original_gate
        assert a2.aspects is original_gate

        # Check aspect added only for a1
        regular1, _ = a1.get_aspects()
        regular2, _ = a2.get_aspects()
        assert len(regular1) == 2  # r1 + new
        assert len(regular2) == 1  # only r1

        # Original gate unchanged
        assert len(original_gate.get_regular()) == 1

    def test_remove_regular_aspect_creates_copy(self):
        class MyAction(AspectGateHost):
            @regular_aspect("r1")
            async def r1(self, params, state, box, connections):
                pass

            @summary_aspect("s")
            async def s(self, params, state, box, connections):
                pass

        a1 = MyAction()
        a2 = MyAction()

        original_gate = MyAction._class_gate

        # Remove aspect from a1
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
            async def r1(self, params, state, box, connections):
                pass

            @summary_aspect("s1")
            async def s1(self, params, state, box, connections):
                pass

        a1 = MyAction()
        a2 = MyAction()

        async def new_summary(params, state, box, connections):
            pass

        a1.set_summary_aspect(new_summary, "new summary")

        assert a1.aspects is not a2.aspects
        _, summary1 = a1.get_aspects()
        _, summary2 = a2.get_aspects()
        assert summary1[0] is new_summary
        # summary2[0] should be the original summary aspect of the class
        assert summary2[0] is MyAction.s1

    def test_remove_summary_aspect_creates_copy(self):
        class MyAction(AspectGateHost):
            @regular_aspect("r1")
            async def r1(self, params, state, box, connections):
                pass

            @summary_aspect("s1")
            async def s1(self, params, state, box, connections):
                pass

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
            async def r1(self, params, state, box, connections):
                pass

            @summary_aspect("s")
            async def s(self, params, state, box, connections):
                pass

        a = MyAction()

        # First change creates a copy
        async def r2(params, state, box, connections):
            pass

        a.add_regular_aspect(r2, "r2")
        gate1 = a._instance_gate

        # Second change uses the same copy, does not create a new one
        a.remove_regular_aspect(MyAction.r1)
        assert a._instance_gate is gate1

        regular, _ = a.get_aspects()
        assert len(regular) == 1
        assert regular[0][0] is r2