# tests/logging/test_expression_evaluator.py
"""
Tests for ExpressionEvaluator – the safe expression evaluator for iif.

Checks:
- Basic arithmetic and logical operations
- String and number comparisons
- Built-in functions (len, upper, lower, format_number)
- iif construct with various conditions
- Nested iif
- Error handling (invalid expressions, missing variables)
- Argument parsing with quotes and parentheses
"""

import pytest

from action_machine.Core.Exceptions import LogTemplateError
from action_machine.Logging.expression_evaluator import ExpressionEvaluator


class TestExpressionEvaluator:
    """Tests for the iif expression evaluator."""

    # ------------------------------------------------------------------
    # SETUP
    # ------------------------------------------------------------------

    def setup_method(self) -> None:
        """Creates a fresh ExpressionEvaluator before each test."""
        self.evaluator = ExpressionEvaluator()

    # ------------------------------------------------------------------
    # TESTS: evaluate() – simple expressions
    # ------------------------------------------------------------------

    def test_evaluate_simple_condition(self) -> None:
        """Check simple numeric condition."""
        names: dict[str, object] = {"amount": 1500}
        result = self.evaluator.evaluate("amount > 1000", names)
        assert result is True

        result = self.evaluator.evaluate("amount <= 1000", names)
        assert result is False

    def test_evaluate_arithmetic(self) -> None:
        """Check arithmetic operations."""
        names = {"x": 10, "y": 3}

        assert self.evaluator.evaluate("x + y", names) == 13
        assert self.evaluator.evaluate("x - y", names) == 7
        assert self.evaluator.evaluate("x * y", names) == 30
        assert self.evaluator.evaluate("x / y", names) == 10 / 3
        assert self.evaluator.evaluate("x % y", names) == 1

    def test_evaluate_string_comparison(self) -> None:
        """Check string comparison."""
        names: dict[str, object] = {"status": "active"}

        result = self.evaluator.evaluate("status == 'active'", names)
        assert result is True

        result = self.evaluator.evaluate("status != 'active'", names)
        assert result is False

    def test_evaluate_logical_operators(self) -> None:
        """Check logical operators."""
        names = {"x": 5, "y": 10}

        result = self.evaluator.evaluate("x > 3 and y < 20", names)
        assert result is True

        result = self.evaluator.evaluate("x > 10 or y < 5", names)
        assert result is False

        result = self.evaluator.evaluate("not (x > 10)", names)
        assert result is True

    def test_evaluate_parentheses(self) -> None:
        """Check operator precedence with parentheses."""
        names = {"x": 5, "y": 10, "z": 2}

        assert self.evaluator.evaluate("x + y * z", names) == 25  # 5 + 20
        assert self.evaluator.evaluate("(x + y) * z", names) == 30  # 15 * 2

    # ------------------------------------------------------------------
    # TESTS: evaluate() – built-in functions
    # ------------------------------------------------------------------

    def test_evaluate_builtin_functions(self) -> None:
        """Check built-in functions len, upper, lower."""
        names = {"text": "Hello", "items": [1, 2, 3]}

        result = self.evaluator.evaluate("len(items)", names)
        assert result == 3

        result = self.evaluator.evaluate("upper(text)", names)
        assert result == "HELLO"

        result = self.evaluator.evaluate("lower(text)", names)
        assert result == "hello"

    def test_evaluate_str_function(self) -> None:
        """Check str() function."""
        names = {"num": 42, "flag": True}

        assert self.evaluator.evaluate("str(num)", names) == "42"
        assert self.evaluator.evaluate("str(flag)", names) == "True"
        assert self.evaluator.evaluate("str(None)", names) == "None"

    def test_evaluate_int_function(self) -> None:
        """Check int() function."""
        names = {"s": "123", "f": 45.67}

        assert self.evaluator.evaluate("int(s)", names) == 123
        assert self.evaluator.evaluate("int(f)", names) == 45

    def test_evaluate_float_function(self) -> None:
        """Check float() function."""
        names = {"s": "123.45", "i": 67}

        assert self.evaluator.evaluate("float(s)", names) == 123.45
        assert self.evaluator.evaluate("float(i)", names) == 67.0

    def test_evaluate_abs_function(self) -> None:
        """Check abs() function."""
        names = {"x": -42, "y": 3.14}

        assert self.evaluator.evaluate("abs(x)", names) == 42
        assert self.evaluator.evaluate("abs(y)", names) == 3.14

    def test_evaluate_format_number(self) -> None:
        """Check format_number() function."""
        names = {"value": 1234567.89}

        # Without decimal places (rounding)
        result = self.evaluator.evaluate("format_number(value, 0)", names)
        assert result == "1,234,568"  # rounded

        # With two decimal places
        result = self.evaluator.evaluate("format_number(value, 2)", names)
        assert result == "1,234,567.89"

        # Negative number
        names2 = {"value": -9876.54}
        result = self.evaluator.evaluate("format_number(value, 1)", names2)
        assert result == "-9,876.5"

    # ------------------------------------------------------------------
    # TESTS: evaluate_iif() – basic construct
    # ------------------------------------------------------------------

    def test_iif_basic(self) -> None:
        """Check basic iif construct."""
        names = {"amount": 1500}
        result = self.evaluator.evaluate_iif("amount > 1000; 'HIGH'; 'LOW'", names)
        assert result == "HIGH"

        names2 = {"amount": 500}
        result = self.evaluator.evaluate_iif("amount > 1000; 'HIGH'; 'LOW'", names2)
        assert result == "LOW"

    def test_iif_without_quotes_in_branches(self) -> None:
        """Branches can be without quotes (numbers, variables)."""
        names = {"value": 10, "threshold": 5}

        result = self.evaluator.evaluate_iif("value > threshold; value * 2; value / 2", names)
        assert result == "20"

        names2 = {"value": 2}
        result = self.evaluator.evaluate_iif("value > 5; value * 2; value / 2", names2)
        assert result == "1.0"

    def test_iif_with_boolean_literals(self) -> None:
        """Check iif with boolean literals True/False."""
        names = {"success": True}
        result = self.evaluator.evaluate_iif("success == True; 'OK'; 'FAIL'", names)
        assert result == "OK"

        names2 = {"success": False}
        result = self.evaluator.evaluate_iif("success == True; 'OK'; 'FAIL'", names2)
        assert result == "FAIL"

    def test_iif_with_boolean_direct(self) -> None:
        """Condition can be a simple boolean variable."""
        names = {"enabled": True}
        result = self.evaluator.evaluate_iif("enabled; 'ON'; 'OFF'", names)
        assert result == "ON"

        names2 = {"enabled": False}
        result = self.evaluator.evaluate_iif("enabled; 'ON'; 'OFF'", names2)
        assert result == "OFF"

    # ------------------------------------------------------------------
    # TESTS: evaluate_iif() – nested constructs
    # ------------------------------------------------------------------

    def test_iif_nested(self) -> None:
        """Check nested iif."""
        names = {"amount": 1500000}
        expr = "amount > 1000000; 'CRITICAL'; iif(amount > 100000; 'HIGH'; 'NORMAL')"

        result = self.evaluator.evaluate_iif(expr, names)
        assert result == "CRITICAL"

        names2 = {"amount": 500000}
        result = self.evaluator.evaluate_iif(expr, names2)
        assert result == "HIGH"

        names3 = {"amount": 50000}
        result = self.evaluator.evaluate_iif(expr, names3)
        assert result == "NORMAL"

    def test_iif_deeply_nested(self) -> None:
        """Deeply nested iif (three levels)."""
        names = {"x": 150}
        expr = "x > 100; 'A'; iif(x > 50; 'B'; iif(x > 10; 'C'; 'D'))"

        assert self.evaluator.evaluate_iif(expr, names) == "A"

        names2 = {"x": 75}
        assert self.evaluator.evaluate_iif(expr, names2) == "B"

        names3 = {"x": 30}
        assert self.evaluator.evaluate_iif(expr, names3) == "C"

        names4 = {"x": 5}
        assert self.evaluator.evaluate_iif(expr, names4) == "D"

    # ------------------------------------------------------------------
    # TESTS: evaluate_iif() – complex conditions
    # ------------------------------------------------------------------

    def test_iif_with_complex_condition(self) -> None:
        """iif condition can contain logical operators."""
        names = {"age": 25, "has_license": True}

        result = self.evaluator.evaluate_iif("age >= 18 and has_license; 'CAN_DRIVE'; 'CANNOT_DRIVE'", names)
        assert result == "CAN_DRIVE"

        names2 = {"age": 16, "has_license": True}
        result = self.evaluator.evaluate_iif("age >= 18 and has_license; 'CAN_DRIVE'; 'CANNOT_DRIVE'", names2)
        assert result == "CANNOT_DRIVE"

    def test_iif_with_arithmetic_in_condition(self) -> None:
        """Arithmetic can be used in the condition."""
        names = {"a": 10, "b": 20, "c": 5}

        result = self.evaluator.evaluate_iif("a + b > c * 5; 'YES'; 'NO'", names)
        # 10 + 20 = 30, c * 5 = 25 → 30 > 25 → YES
        assert result == "YES"

    # ------------------------------------------------------------------
    # TESTS: evaluate_iif() – strings
    # ------------------------------------------------------------------

    def test_iif_with_strings_containing_semicolon(self) -> None:
        """Strings in branches can contain semicolons."""
        names = {"lang": "ru"}

        result = self.evaluator.evaluate_iif("lang == 'ru'; 'Привет; как дела?'; 'Hello; how are you?'", names)
        assert result == "Привет; как дела?"

    def test_iif_with_strings_containing_quotes(self) -> None:
        """Strings in branches can contain escaped quotes."""
        names = {"lang": "ru"}

        result = self.evaluator.evaluate_iif("lang == 'ru'; 'Он сказал: \"Привет\"'; 'He said: \"Hello\"'", names)
        assert result == 'Он сказал: "Привет"'

    # ------------------------------------------------------------------
    # TESTS: process_template() – replacing iif in text
    # ------------------------------------------------------------------

    def test_process_template_no_iif(self) -> None:
        """Template without iif is returned unchanged."""
        template = "Simple message"
        result = self.evaluator.process_template(template, {})
        assert result == template

    def test_process_template_single_iif(self) -> None:
        """Template with one iif."""
        names = {"success": True}
        template = "Status: {iif(success == True; 'OK'; 'FAIL')}"
        result = self.evaluator.process_template(template, names)
        assert result == "Status: OK"

    def test_process_template_multiple_iif(self) -> None:
        """Template with multiple iif constructs."""
        names = {"x": 5, "y": 10}
        template = "{iif(x > 3; 'A'; 'B')} and {iif(y < 5; 'C'; 'D')}"
        result = self.evaluator.process_template(template, names)
        assert result == "A and D"

    def test_process_template_iif_at_beginning(self) -> None:
        """iif at the beginning of the string."""
        names = {"count": 150}
        template = "{iif(count > 100; 'Many'; 'Few')} items"
        result = self.evaluator.process_template(template, names)
        assert result == "Many items"

    def test_process_template_iif_at_end(self) -> None:
        """iif at the end of the string."""
        names = {"success": False}
        template = "Result: {iif(success; 'OK'; 'Error')}"
        result = self.evaluator.process_template(template, names)
        assert result == "Result: Error"

    # ------------------------------------------------------------------
    # TESTS: Error handling
    # ------------------------------------------------------------------

    def test_iif_syntax_error_raises(self) -> None:
        """
        iif with wrong number of arguments raises LogTemplateError.
        """
        names: dict[str, object] = {}

        with pytest.raises(LogTemplateError, match="iif expects 3 arguments"):
            self.evaluator.evaluate_iif("amount > 1000; 'HIGH'", names)

    def test_iif_undefined_variable_raises(self) -> None:
        """
        Referencing an undefined variable in iif raises LogTemplateError.
        """
        names: dict[str, object] = {}

        with pytest.raises(LogTemplateError, match="Error evaluating expression"):
            self.evaluator.evaluate_iif("missing > 10; 'yes'; 'no'", names)

    def test_evaluate_invalid_expression_raises(self) -> None:
        """
        Invalid expression in evaluate raises LogTemplateError.
        """
        with pytest.raises(LogTemplateError, match="Error evaluating expression"):
            self.evaluator.evaluate(">>>invalid<<<", {})

    def test_iif_invalid_condition_raises(self) -> None:
        """
        Invalid condition in iif raises LogTemplateError.
        """
        names = {"x": 10}

        with pytest.raises(LogTemplateError, match="Error evaluating expression"):
            self.evaluator.evaluate_iif("x >>> 5; 'A'; 'B'", names)

    def test_iif_division_by_zero_raises(self) -> None:
        """
        Division by zero in iif raises LogTemplateError.
        """
        names = {"x": 10, "y": 0}

        with pytest.raises(LogTemplateError, match="Error evaluating expression"):
            self.evaluator.evaluate_iif("y == 0; x / y; x * 2", names)

    # ------------------------------------------------------------------
    # TESTS: Literal values (without names)
    # ------------------------------------------------------------------

    def test_iif_with_literal_values(self) -> None:
        """
        Check iif with already substituted literal values.
        simpleeval receives numbers/strings as literals, names={}.
        """
        # Numeric comparison – values already substituted as literals
        result = self.evaluator.evaluate_iif("1500.0 > 1000; 'HIGH'; 'LOW'", {})
        assert result == "HIGH"

        result = self.evaluator.evaluate_iif("500.0 > 1000; 'HIGH'; 'LOW'", {})
        assert result == "LOW"

    def test_iif_with_literal_string_comparison(self) -> None:
        """
        Check iif with string comparison via literals.
        """
        result = self.evaluator.evaluate_iif("'admin' == 'admin'; 'ROOT'; 'USER'", {})
        assert result == "ROOT"

        result = self.evaluator.evaluate_iif("'agent_1' == 'admin'; 'ROOT'; 'USER'", {})
        assert result == "USER"

    def test_iif_with_literal_bool(self) -> None:
        """
        Check iif with boolean literals.
        """
        result = self.evaluator.evaluate_iif("True == True; 'OK'; 'FAIL'", {})
        assert result == "OK"

        result = self.evaluator.evaluate_iif("False == True; 'OK'; 'FAIL'", {})
        assert result == "FAIL"

    def test_iif_with_literal_arithmetic(self) -> None:
        """Check iif with arithmetic on literals."""
        result = self.evaluator.evaluate_iif("10 + 20 > 25; 'YES'; 'NO'", {})
        assert result == "YES"

    # ------------------------------------------------------------------
    # TESTS: process_template with errors
    # ------------------------------------------------------------------

    def test_process_template_invalid_iif_raises(self) -> None:
        """
        Invalid iif inside template raises LogTemplateError.
        """
        with pytest.raises(LogTemplateError):
            self.evaluator.process_template("Result: {iif(missing > 10; 'yes'; 'no')}", {})

    def test_process_template_with_malformed_iif_raises(self) -> None:
        """
        iif with incorrect syntax inside template raises error.
        """
        with pytest.raises(LogTemplateError):
            self.evaluator.process_template("Bad: {iif(x > 10; 'yes')}", {})