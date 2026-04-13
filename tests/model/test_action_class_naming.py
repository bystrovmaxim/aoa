# tests/model/test_action_class_naming.py
"""
Naming invariant: subclasses of ``BaseAction`` must use the ``Action`` class suffix.

Enforced in ``__init_subclass__``. Violations raise ``NamingSuffixError``.
"""

import pytest

from action_machine.model.exceptions import NamingSuffixError


class TestActionSuffix:
    """Every class inheriting BaseAction must end with 'Action'."""

    def test_correct_suffix_passes(self) -> None:
        """Name 'MyTaskAction' — class definition succeeds."""
        from action_machine.model.base_action import BaseAction
        from action_machine.model.base_params import BaseParams
        from action_machine.model.base_result import BaseResult

        class MyTaskAction(BaseAction[BaseParams, BaseResult]):
            pass

        assert MyTaskAction.__name__.endswith("Action")

    def test_missing_suffix_raises(self) -> None:
        """Name 'MyTask' without 'Action' suffix → NamingSuffixError."""
        from action_machine.model.base_action import BaseAction
        from action_machine.model.base_params import BaseParams
        from action_machine.model.base_result import BaseResult

        with pytest.raises(NamingSuffixError, match="Action"):
            class MyTask(BaseAction[BaseParams, BaseResult]):
                pass

    def test_wrong_suffix_raises(self) -> None:
        """Name 'MyTaskHandler' → NamingSuffixError (suffix is not 'Action')."""
        from action_machine.model.base_action import BaseAction
        from action_machine.model.base_params import BaseParams
        from action_machine.model.base_result import BaseResult

        with pytest.raises(NamingSuffixError, match="Action"):
            class MyTaskHandler(BaseAction[BaseParams, BaseResult]):
                pass

    def test_indirect_subclass_checked(self) -> None:
        """Indirect BaseAction subclass without suffix → NamingSuffixError."""
        from action_machine.model.base_action import BaseAction
        from action_machine.model.base_params import BaseParams
        from action_machine.model.base_result import BaseResult

        class BaseTaskAction(BaseAction[BaseParams, BaseResult]):
            pass

        with pytest.raises(NamingSuffixError, match="Action"):
            class SpecificTask(BaseTaskAction):
                pass
