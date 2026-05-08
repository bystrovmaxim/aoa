# tests/model/test_action_class_naming.py
"""
Naming invariant: subclasses of ``BaseAction`` must use the ``Action`` class suffix.

Enforced in ``__init_subclass__``. Violations raise ``NamingSuffixError``.
"""

import pytest

from aoa.action_machine.exceptions import NamingSuffixError


class TestActionSuffix:
    """Every class inheriting BaseAction must end with 'Action'."""

    def test_correct_suffix_passes(self) -> None:
        """Name 'MyTaskAction' — class definition succeeds."""
        from aoa.action_machine.model.base_action import BaseAction
        from aoa.action_machine.model.params_stub import ParamsStub
        from aoa.action_machine.model.result_stub import ResultStub

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

    def test_wrong_suffix_raises(self) -> None:
        """Name 'MyTaskHandler' → NamingSuffixError (suffix is not 'Action')."""
        from aoa.action_machine.model.base_action import BaseAction
        from aoa.action_machine.model.params_stub import ParamsStub
        from aoa.action_machine.model.result_stub import ResultStub

        with pytest.raises(NamingSuffixError, match="Action"):
            class MyTaskHandler(BaseAction[ParamsStub, ResultStub]):
                pass

    def test_indirect_subclass_checked(self) -> None:
        """Indirect BaseAction subclass without suffix → NamingSuffixError."""
        from aoa.action_machine.model.base_action import BaseAction
        from aoa.action_machine.model.params_stub import ParamsStub
        from aoa.action_machine.model.result_stub import ResultStub

        class BaseTaskAction(BaseAction[ParamsStub, ResultStub]):
            pass

        with pytest.raises(NamingSuffixError, match="Action"):
            class SpecificTask(BaseTaskAction):
                pass
