# tests/intents/checkers/__init__.py
"""
Tests for ActionMachine aspect result checkers.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers all six result checker types. Each checker validates one field in the dict
returned by an aspect method. The machine builds checker instances from CheckerMeta
and calls checker.check(result_dict) after each aspect.

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

ResultStringChecker / result_string
    Ensures the field is a string. Extra params: not_empty, min_length, max_length.
    Empty string with not_empty=True is an error.

ResultIntChecker / result_int
    Ensures the field is an int (not bool). Extra params: min_value, max_value.

ResultFloatChecker / result_float
    Ensures the field is numeric (int or float). Extra params: min_value, max_value.
    bool passes isinstance in Python by design (bool is a subclass of int).

ResultBoolChecker / result_bool
    Ensures the field is strictly bool. Numbers (0, 1), strings ("true", "false"),
    and other types are rejected — only isinstance(value, bool).

ResultDateChecker / result_date
    Ensures the field is a datetime or a string parseable with date_format.
    Extra params: date_format, min_date, max_date.

ResultInstanceChecker / result_instance
    Ensures the field is an instance of the given class (or tuple of classes).
    Uses isinstance including subclasses. Extra param: expected_class.

═══════════════════════════════════════════════════════════════════════════════
SHARED CHECKER CONTRACT
═══════════════════════════════════════════════════════════════════════════════

All checkers inherit ResultFieldChecker and share:

    checker = SomeChecker(field_name, required=True, **extra_params)
    checker.check(result_dict)  # ValidationFieldError on violation

check() steps:
    1. Field presence (required).
    2. Value not None (required).
    3. _check_type_and_constraints(value) — type-specific checks.

═══════════════════════════════════════════════════════════════════════════════
SHARED DECORATOR CONTRACT
═══════════════════════════════════════════════════════════════════════════════

Each decorator (result_string, result_int, ...) records metadata in the aspect
method's _checker_meta. MetadataBuilder aggregates into the checker snapshot
(GateCoordinator.get_checkers). The decorator returns the original function unchanged;
multiple decorators on one method accumulate a list of _checker_meta.

═══════════════════════════════════════════════════════════════════════════════
TEST LAYOUT
═══════════════════════════════════════════════════════════════════════════════

    tests/intents/checkers/
    ├── __init__.py                      — this file
    ├── test_result_string_checker.py    — strings, not_empty, min/max_length
    ├── test_result_int_checker.py       — integers, min/max_value
    ├── test_result_float_checker.py     — numbers (int/float), min/max_value
    ├── test_result_bool_checker.py      — bool, strict isinstance
    ├── test_result_date_checker.py      — dates, date_format, min/max_date
    ├── test_result_instance_checker.py  — isinstance, single/tuple of classes
    └── test_checker_class_naming.py     — ResultFieldChecker class name suffix
"""
