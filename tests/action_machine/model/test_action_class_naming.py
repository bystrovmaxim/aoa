# tests/action_machine/model/test_action_class_naming.py
"""
Naming invariant: subclasses of ``BaseAction`` must use the ``Action`` class suffix.

Enforced in ``__init_subclass__``. Violations raise ``NamingSuffixError``.
"""

import pytest

from aoa.action_machine.exceptions import NamingSuffixError
from aoa.graph.exclude_graph_model import exclude_graph_model


def _exclude_leaked_subclass(parent: type, name: str) -> None:
    """``NamingSuffixError`` during class creation can still register a leaked subtype."""
    for sub in parent.__subclasses__():
        if sub.__name__ == name:
            exclude_graph_model(sub)
            return


class TestActionSuffix:
    """Every class inheriting BaseAction must end with 'Action'."""

    def test_correct_suffix_passes(self) -> None:
        """Name 'MyTaskAction' — class definition succeeds."""
        from aoa.action_machine.model.base_action import BaseAction
        from aoa.action_machine.model.params_stub import ParamsStub
        from aoa.action_machine.model.result_stub import ResultStub

        @exclude_graph_model
        class MyTaskAction(BaseAction[ParamsStub, ResultStub]):
            pass

        assert MyTaskAction.__name__.endswith("Action")

    def test_missing_suffix_raises(self) -> None:
        """Name 'MyTask' without 'Action' suffix → NamingSuffixError."""
        from aoa.action_machine.model.base_action import BaseAction
        from aoa.action_machine.model.params_stub import ParamsStub
        from aoa.action_machine.model.result_stub import ResultStub

        with pytest.raises(NamingSuffixError, match="Action"):
            class MyTask(BaseAction[ParamsStub, ResultStub]):
                pass

        _exclude_leaked_subclass(BaseAction, "MyTask")

    def test_wrong_suffix_raises(self) -> None:
        """Name 'MyTaskHandler' → NamingSuffixError (suffix is not 'Action')."""
        from aoa.action_machine.model.base_action import BaseAction
        from aoa.action_machine.model.params_stub import ParamsStub
        from aoa.action_machine.model.result_stub import ResultStub

        with pytest.raises(NamingSuffixError, match="Action"):
            class MyTaskHandler(BaseAction[ParamsStub, ResultStub]):
                pass

        _exclude_leaked_subclass(BaseAction, "MyTaskHandler")

    def test_indirect_subclass_checked(self) -> None:
        """Indirect BaseAction subclass without suffix → NamingSuffixError."""
        from aoa.action_machine.model.base_action import BaseAction
        from aoa.action_machine.model.params_stub import ParamsStub
        from aoa.action_machine.model.result_stub import ResultStub

        @exclude_graph_model
        class BaseTaskAction(BaseAction[ParamsStub, ResultStub]):
            pass

        with pytest.raises(NamingSuffixError, match="Action"):
            class SpecificTask(BaseTaskAction):
                pass

        _exclude_leaked_subclass(BaseTaskAction, "SpecificTask")
