# tests/intents/checkers/test_checker_class_naming.py
"""
Naming invariant: subclasses of ``ResultFieldChecker`` must use the ``Checker`` suffix.

Enforced in ``__init_subclass__``. Violations raise ``NamingSuffixError``.
"""

import pytest

from action_machine.model.exceptions import NamingSuffixError


class TestCheckerSuffix:
    """Every class inheriting ResultFieldChecker must end with 'Checker'."""

    def test_correct_suffix_passes(self) -> None:
        """Name 'ResultEmailChecker' — definition succeeds."""
        from action_machine.intents.checkers.result_field_checker import ResultFieldChecker

        class ResultEmailChecker(ResultFieldChecker):
            def _check_type_and_constraints(self, value):
                pass

        assert ResultEmailChecker.__name__.endswith("Checker")

    def test_missing_suffix_raises(self) -> None:
        """Name 'EmailValidator' without 'Checker' suffix → NamingSuffixError."""
        from action_machine.intents.checkers.result_field_checker import ResultFieldChecker

        with pytest.raises(NamingSuffixError, match="Checker"):
            class EmailValidator(ResultFieldChecker):
                def _check_type_and_constraints(self, value):
                    pass

    def test_existing_checkers_have_suffix(self) -> None:
        """All built-in checkers end with 'Checker'."""
        from action_machine.intents.checkers import (
            ResultBoolChecker,
            ResultDateChecker,
            ResultFloatChecker,
            ResultInstanceChecker,
            ResultIntChecker,
            ResultStringChecker,
        )

        for checker_cls in [
            ResultBoolChecker, ResultDateChecker, ResultFloatChecker,
            ResultInstanceChecker, ResultIntChecker, ResultStringChecker,
        ]:
            assert checker_cls.__name__.endswith("Checker"), (
                f"{checker_cls.__name__} does not end with 'Checker'"
            )
