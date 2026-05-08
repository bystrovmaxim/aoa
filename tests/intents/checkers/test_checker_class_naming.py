# tests/intents/checkers/test_checker_class_naming.py
"""Convention: built-in ``Field*Checker`` names end with ``Checker`` (stable graph labels)."""


def test_existing_checkers_have_suffix() -> None:
    """All built-in checkers end with 'Checker'."""
    from action_machine.intents.checkers import (
        FieldBoolChecker,
        FieldDateChecker,
        FieldFloatChecker,
        FieldInstanceChecker,
        FieldIntChecker,
        FieldStringChecker,
    )

    for checker_cls in (
        FieldBoolChecker,
        FieldDateChecker,
        FieldFloatChecker,
        FieldInstanceChecker,
        FieldIntChecker,
        FieldStringChecker,
    ):
        assert checker_cls.__name__.endswith("Checker"), f"{checker_cls.__name__} does not end with 'Checker'"
