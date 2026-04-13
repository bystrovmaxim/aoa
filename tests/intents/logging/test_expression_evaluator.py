# tests/intents/logging/test_expression_evaluator.py
"""Tests of ExpressionEvaluator - a secure expression evaluator for logging templates.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

ExpressionEvaluator uses the simpleeval library for secure evaluation
expressions inside the {iif(condition; true_value; false_value)} construct.
Provides:

- Comparison operators, logical, arithmetic.
- Built-in functions: len, upper, lower, format_number, str, int, float, abs.
- Color functions: red, green, blue, etc. (wrapped in markers).
- Function debug(obj) - introspection of objects.
- Function exists(name) - checking the existence of a variable.

All calculations are safe: simpleeval does not provide access to the file system,
network and built-in dangerous functions.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

evaluate() - simple expressions:
    - Numerical comparisons.
    - Arithmetic operations.
    - Logical operators (and, or, not).
    - String comparisons.
    - Built-in functions (len, upper, lower, format_number, str, int, float, abs).
    - Color functions (wrapped in marker __COLOR(...)__COLOR_END__).

evaluate_iif() - iif construct:
    - Basic iif with literals and variables.
    - Nested iifs.
    - Parsing arguments taking into account nested parentheses and string literals.
    - Handling lines with semicolons inside.

process_template() - replacing all {iif(...)} in the line:
    - Single iif.
    - Several iif.
    - iif at the beginning/end of the line.

Errors:
    - Invalid number of arguments iif → LogTemplateError.
    - Undefined variable → LogTemplateError.
    - Syntax error in expression → LogTemplateError.
    - Division by zero → LogTemplateError."""

import pytest

from action_machine.intents.logging.expression_evaluator import ExpressionEvaluator, _IifArgSplitter
from action_machine.model.exceptions import LogTemplateError


@pytest.fixture
def evaluator() -> ExpressionEvaluator:
    """Fresh ExpressionEvaluator for each test."""
    return ExpressionEvaluator()


# ======================================================================
#TESTS: evaluate() - simple expressions
# ======================================================================

class TestEvaluateSimple:
    """Basic arithmetic and logical expressions."""

    def test_numeric_comparison(self, evaluator: ExpressionEvaluator) -> None:
        """Comparison of numbers."""
        names = {"amount": 1500}
        assert evaluator.evaluate("amount > 1000", names) is True
        assert evaluator.evaluate("amount <= 1000", names) is False

    def test_arithmetic(self, evaluator: ExpressionEvaluator) -> None:
        """Arithmetic operations."""
        names = {"x": 10, "y": 3}
        assert evaluator.evaluate("x + y", names) == 13
        assert evaluator.evaluate("x - y", names) == 7
        assert evaluator.evaluate("x * y", names) == 30
        assert evaluator.evaluate("x / y", names) == 10 / 3
        assert evaluator.evaluate("x % y", names) == 1

    def test_string_comparison(self, evaluator: ExpressionEvaluator) -> None:
        """String comparison."""
        names = {"status": "active"}
        assert evaluator.evaluate("status == 'active'", names) is True
        assert evaluator.evaluate("status != 'active'", names) is False

    def test_logical_operators(self, evaluator: ExpressionEvaluator) -> None:
        """Logical operators."""
        names = {"x": 5, "y": 10}
        assert evaluator.evaluate("x > 3 and y < 20", names) is True
        assert evaluator.evaluate("x > 10 or y < 5", names) is False
        assert evaluator.evaluate("not (x > 10)", names) is True

    def test_parentheses(self, evaluator: ExpressionEvaluator) -> None:
        """Priority of operations with parentheses."""
        names = {"x": 5, "y": 10, "z": 2}
        assert evaluator.evaluate("x + y * z", names) == 25
        assert evaluator.evaluate("(x + y) * z", names) == 30


class TestEvaluateBuiltins:
    """Built-in functions."""

    def test_len_upper_lower(self, evaluator: ExpressionEvaluator) -> None:
        """len, upper, lower."""
        names = {"text": "Hello", "items": [1, 2, 3]}
        assert evaluator.evaluate("len(items)", names) == 3
        assert evaluator.evaluate("upper(text)", names) == "HELLO"
        assert evaluator.evaluate("lower(text)", names) == "hello"

    def test_str_int_float_abs(self, evaluator: ExpressionEvaluator) -> None:
        """str, int, float, abs."""
        names = {"s": "123", "f": 45.67, "x": -42}
        assert evaluator.evaluate("str(42)", names) == "42"
        assert evaluator.evaluate("int(s)", names) == 123
        assert evaluator.evaluate("int(f)", names) == 45
        assert evaluator.evaluate("float(s)", names) == 123.0
        assert evaluator.evaluate("abs(x)", names) == 42

    def test_format_number(self, evaluator: ExpressionEvaluator) -> None:
        """format_number(value, decimals)."""
        names = {"value": 1234567.89}
        assert evaluator.evaluate("format_number(value, 0)", names) == "1,234,568"
        assert evaluator.evaluate("format_number(value, 2)", names) == "1,234,567.89"

    def test_color_functions_return_markers(self, evaluator: ExpressionEvaluator) -> None:
        """Color functions return __COLOR(color)text__COLOR_END__ markers."""
        names = {}
        assert evaluator.evaluate("red('alert')", names) == "__COLOR(red)alert__COLOR_END__"
        assert evaluator.evaluate("green('ok')", names) == "__COLOR(green)ok__COLOR_END__"


# ======================================================================
#TESTS: evaluate_iif() - iif construct
# ======================================================================

class TestEvaluateIifBasic:
    """Basic designs iif."""

    def test_iif_with_literals(self, evaluator: ExpressionEvaluator) -> None:
        """iif with literals."""
        assert evaluator.evaluate_iif("1 > 0; 'yes'; 'no'", {}) == "yes"
        assert evaluator.evaluate_iif("1 < 0; 'yes'; 'no'", {}) == "no"

    def test_iif_with_variables(self, evaluator: ExpressionEvaluator) -> None:
        """iif with variables."""
        names = {"amount": 1500}
        assert evaluator.evaluate_iif("amount > 1000; 'HIGH'; 'LOW'", names) == "HIGH"

    def test_iif_without_quotes_in_branches(self, evaluator: ExpressionEvaluator) -> None:
        """Branches can be without quotes (numbers, variables)."""
        names = {"value": 10, "threshold": 5}
        assert evaluator.evaluate_iif("value > threshold; value * 2; value / 2", names) == "20"

    def test_iif_with_boolean_literals(self, evaluator: ExpressionEvaluator) -> None:
        """Boolean literals."""
        names = {"success": True}
        assert evaluator.evaluate_iif("success == True; 'OK'; 'FAIL'", names) == "OK"
        assert evaluator.evaluate_iif("success; 'OK'; 'FAIL'", names) == "OK"

    def test_iif_with_complex_condition(self, evaluator: ExpressionEvaluator) -> None:
        """Complex condition with and/or."""
        names = {"age": 25, "has_license": True}
        assert evaluator.evaluate_iif("age >= 18 and has_license; 'CAN_DRIVE'; 'CANNOT_DRIVE'", names) == "CAN_DRIVE"


class TestEvaluateIifNested:
    """Nested iifs."""

    def test_nested_iif(self, evaluator: ExpressionEvaluator) -> None:
        """One level of nesting."""
        names = {"amount": 1500000}
        expr = "amount > 1000000; 'CRITICAL'; iif(amount > 100000; 'HIGH'; 'NORMAL')"
        assert evaluator.evaluate_iif(expr, names) == "CRITICAL"

        names2 = {"amount": 500000}
        assert evaluator.evaluate_iif(expr, names2) == "HIGH"

        names3 = {"amount": 50000}
        assert evaluator.evaluate_iif(expr, names3) == "NORMAL"

    def test_deeply_nested_iif(self, evaluator: ExpressionEvaluator) -> None:
        """Deeply nested iifs (three levels)."""
        expr = "x > 100; 'A'; iif(x > 50; 'B'; iif(x > 10; 'C'; 'D'))"
        assert evaluator.evaluate_iif(expr, {"x": 150}) == "A"


class TestEvaluateIifStringHandling:
    """Handling strings with quotes and semicolons."""

    def test_string_with_semicolon(self, evaluator: ExpressionEvaluator) -> None:
        """String literals can contain semicolons."""
        names = {"lang": "ru"}
        expr = "lang == 'ru'; 'Hello; How are you?'; 'Hello; how are you?'"
        assert evaluator.evaluate_iif(expr, names) == "Hello; How are you?"

    def test_string_with_quotes(self, evaluator: ExpressionEvaluator) -> None:
        """Strings can contain quotes (escaped)."""
        names = {"lang": "ru"}
        expr = "lang == 'ru'; 'He said: \"Hello\"'; 'He said: \"Hello\"'"
        assert evaluator.evaluate_iif(expr, names) == 'He said: "Hello"'


# ======================================================================
#TESTS: process_template() - replacing iif in line
# ======================================================================

class TestProcessTemplate:
    """Replace all {iif(...)} in a string."""

    def test_no_iif(self, evaluator: ExpressionEvaluator) -> None:
        """A template without iif is returned unchanged."""
        template = "Simple message"
        assert evaluator.process_template(template, {}) == template

    def test_single_iif(self, evaluator: ExpressionEvaluator) -> None:
        """One iif in the middle of the line."""
        names = {"success": True}
        template = "Status: {iif(success == True; 'OK'; 'FAIL')}"
        assert evaluator.process_template(template, names) == "Status: OK"

    def test_multiple_iif(self, evaluator: ExpressionEvaluator) -> None:
        """Multiple iifs on one line."""
        names = {"x": 5, "y": 10}
        template = "{iif(x > 3; 'A'; 'B')} and {iif(y < 5; 'C'; 'D')}"
        assert evaluator.process_template(template, names) == "A and D"

    def test_iif_at_beginning(self, evaluator: ExpressionEvaluator) -> None:
        """iif at the beginning of the line."""
        names = {"count": 150}
        template = "{iif(count > 100; 'Many'; 'Few')} items"
        assert evaluator.process_template(template, names) == "Many items"

    def test_iif_at_end(self, evaluator: ExpressionEvaluator) -> None:
        """iif at the end of the line."""
        names = {"success": False}
        template = "Result: {iif(success; 'OK'; 'Error')}"
        assert evaluator.process_template(template, names) == "Result: Error"


# ======================================================================
#TESTS: Parsing iif arguments (_IifArgSplitter)
# ======================================================================

class TestIifArgSplitter:
    """Parse the iif argument string, taking into account nested parentheses and quotes."""

    def test_split_with_nested_parens(self) -> None:
        """Nested parentheses in a condition do not interfere with separation."""
        raw = "a + (b * c) > 10; 'yes'; 'no'"
        splitter = _IifArgSplitter(raw)
        parts = splitter.split()
        assert len(parts) == 3
        assert parts[0] == "a + (b * c) > 10"
        assert parts[1].strip() == "'yes'"
        assert parts[2].strip() == "'no'"

    def test_split_with_string_containing_semicolon(self) -> None:
        """String literals with semicolons do not break arguments."""
        raw = "lang == 'ru'; 'Hello; How are you?'; 'Hello; how are you?'"
        splitter = _IifArgSplitter(raw)
        parts = splitter.split()
        assert len(parts) == 3
        assert parts[0] == "lang == 'ru'"
        assert parts[1].strip() == "'Hello; How are you?'"
        assert parts[2].strip() == "'Hello; how are you?'"

    def test_split_with_nested_iif(self) -> None:
        """Nested iif in the second branch."""
        raw = "amount > 1000; 'HIGH'; iif(amount > 500; 'MEDIUM'; 'LOW')"
        splitter = _IifArgSplitter(raw)
        parts = splitter.split()
        assert len(parts) == 3
        assert parts[0] == "amount > 1000"
        assert parts[1] == " 'HIGH'"
        assert parts[2] == " iif(amount > 500; 'MEDIUM'; 'LOW')"


# ======================================================================
#TESTS: Error Handling
# ======================================================================

class TestErrorHandling:
    """ExpressionEvaluator throws LogTemplateError on errors."""

    def test_iif_wrong_number_of_args(self, evaluator: ExpressionEvaluator) -> None:
        """iif with 2 arguments instead of 3 → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="iif expects 3 arguments"):
            evaluator.evaluate_iif("amount > 1000; 'HIGH'", {})

    def test_iif_undefined_variable(self, evaluator: ExpressionEvaluator) -> None:
        """Variable is not defined → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="Variable 'missing' not found"):
            evaluator.evaluate_iif("missing > 10; 'yes'; 'no'", {})

    def test_evaluate_invalid_expression(self, evaluator: ExpressionEvaluator) -> None:
        """Syntactically incorrect expression → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="Error evaluating expression"):
            evaluator.evaluate(">>>invalid<<<", {})

    def test_iif_division_by_zero(self, evaluator: ExpressionEvaluator) -> None:
        """Division by zero → LogTemplateError."""
        names = {"x": 10, "y": 0}
        with pytest.raises(LogTemplateError, match="Error evaluating expression"):
            evaluator.evaluate_iif("y == 0; x / y; x * 2", names)

    def test_process_template_invalid_iif(self, evaluator: ExpressionEvaluator) -> None:
        """Invalid iif inside the template → LogTemplateError."""
        with pytest.raises(LogTemplateError):
            evaluator.process_template("Bad: {iif(x > 10; 'yes')}", {})

    def test_process_template_missing_variable(self, evaluator: ExpressionEvaluator) -> None:
        """Variable is not defined in iif -> LogTemplateError."""
        with pytest.raises(LogTemplateError):
            evaluator.process_template("Result: {iif(missing > 10; 'yes'; 'no')}", {})
            evaluator.process_template("Result: {iif(missing > 10; 'yes'; 'no')}", {})
