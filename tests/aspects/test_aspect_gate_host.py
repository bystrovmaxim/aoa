# tests/aspects/test_aspect_gate_host.py
"""
Tests for AspectGateHost — the host for aspect gate.

Checks:
- Aspect registration via decorators
- Error when summary aspect is missing
- Error when two summary aspects are defined
- Aspects are not inherited from parent classes
- Per-instance aspect modification methods are NOT available
- Aspect data is shared across instances (cached in class)
"""

import pytest

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.Core.ToolsBox import ToolsBox


class TestAspectGateHost:
    """Tests for the aspect gate host."""

    def test_instances_share_aspect_data(self):
        """All instances of the same class return the same aspect data."""
        class MyAction(AspectGateHost):
            @regular_aspect("shared")
            async def shared(self, params, state, box: ToolsBox, connections):
                pass
            @summary_aspect("shared_summary")
            async def summ(self, params, state, box: ToolsBox, connections):
                pass

        action1 = MyAction()
        action2 = MyAction()

        reg1, sum1 = action1.get_aspects()
        reg2, sum2 = action2.get_aspects()

        # The lists/tuples are cached per class, so they should be the same objects
        assert reg1 is reg2
        assert sum1 is sum2
        assert len(reg1) == 1
        assert reg1[0][0].__name__ == "shared"
        assert sum1[0].__name__ == "summ"

    def test_get_aspects_empty(self):
        """Action with only summary aspect returns empty regular list."""
        class MyAction(AspectGateHost):
            @summary_aspect("test")
            async def summ(self, params, state, box: ToolsBox, connections):
                pass

        action = MyAction()
        regular, summary = action.get_aspects()
        assert regular == []
        assert summary is not None
        assert summary[0].__name__ == "summ"
        assert summary[1] == "test"

    def test_get_aspects_with_regular_and_summary(self):
        """Action with both regular and summary aspects returns correct lists."""
        class MyAction(AspectGateHost):
            @regular_aspect("first")
            async def first(self, params, state, box: ToolsBox, connections):
                pass

            @regular_aspect("second")
            async def second(self, params, state, box: ToolsBox, connections):
                pass

            @summary_aspect("summary")
            async def summ(self, params, state, box: ToolsBox, connections):
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

    def test_missing_summary_raises_on_instance_creation(self):
        """Action with regular aspects but no summary raises TypeError when instantiated."""
        class MyAction(AspectGateHost):
            @regular_aspect("only")
            async def only(self, params, state, box: ToolsBox, connections):
                pass

        with pytest.raises(TypeError, match="does not have a summary aspect"):
            MyAction()  # instance creation triggers check in __init__

    def test_child_must_have_own_summary(self):
        """Child class does not inherit summary aspect from parent; must define its own."""
        class Parent(AspectGateHost):
            @summary_aspect("parent_summary")
            async def parent_summary(self, params, state, box: ToolsBox, connections):
                pass

        # Child has regular aspects but no summary → error
        with pytest.raises(TypeError, match="does not have a summary aspect"):
            class Child(Parent):
                @regular_aspect("child")
                async def child_aspect(self, params, state, box: ToolsBox, connections):
                    pass

            Child()

    def test_duplicate_summary_in_single_class_raises(self):
        """Cannot define two summary aspects in one class."""
        with pytest.raises(TypeError, match="Only one summary aspect can be registered per action"):
            class MyAction(AspectGateHost):
                @summary_aspect("first")
                async def summ1(self, params, state, box: ToolsBox, connections):
                    pass

                @summary_aspect("second")
                async def summ2(self, params, state, box: ToolsBox, connections):
                    pass

    def test_temporary_meta_removed_after_class_creation(self):
        """After class creation, the temporary _new_aspect_meta attribute is removed."""
        class MyAction(AspectGateHost):
            @regular_aspect("test")
            async def test(self, params, state, box: ToolsBox, connections):
                pass

            @summary_aspect("summary")
            async def summ(self, params, state, box: ToolsBox, connections):
                pass

        assert not hasattr(MyAction.test, '_new_aspect_meta')
        assert not hasattr(MyAction.summ, '_new_aspect_meta')

    def test_no_per_instance_modification_methods(self):
        """Per-instance aspect modification methods must not exist."""
        class MyAction(AspectGateHost):
            @summary_aspect("test")
            async def summ(self, params, state, box: ToolsBox, connections):
                pass

        action = MyAction()

        # Check that the methods that allowed per-instance changes are gone
        assert not hasattr(action, 'add_regular_aspect')
        assert not hasattr(action, 'remove_regular_aspect')
        assert not hasattr(action, 'set_summary_aspect')
        assert not hasattr(action, 'remove_summary_aspect')
        assert not hasattr(action, '_ensure_copy')
        assert not hasattr(action, '_instance_gate')