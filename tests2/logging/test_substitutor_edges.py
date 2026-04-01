# tests2/logging/test_substitutor_edges.py
"""
Additional edge-case tests for VariableSubstitutor and ExpressionEvaluator.

Scenarios covered:
    VariableSubstitutor: error handling, successful substitution, iif via substitute.
    ExpressionEvaluator: evaluate() direct, evaluate_iif() direct, process_template.
"""

import pytest

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.core.exceptions import LogTemplateError
from action_machine.logging.expression_evaluator import ExpressionEvaluator
from action_machine.logging.log_scope import LogScope
from action_machine.logging.variable_substitutor import VariableSubstitutor


@pytest.fixture()
def substitutor() -> VariableSubstitutor:
    return VariableSubstitutor()


@pytest.fixture()
def evaluator() -> ExpressionEvaluator:
    return ExpressionEvaluator()


@pytest.fixture()
def scope() -> LogScope:
    return LogScope(
        machine="TestMachine",
        mode="test",
        action="TestAction",
        aspect="test_aspect",
        nest_level=0,
    )


@pytest.fixture()
def ctx() -> Context:
    return Context()


@pytest.fixture()
def state() -> BaseState:
    return BaseState({})


@pytest.fixture()
def params() -> BaseParams:
    return BaseParams()


class TestSubstitutorErrors:
    """Verify error handling for invalid templates."""

    def test_unknown_namespace(self, substitutor, scope, ctx, state, params) -> None:
        with pytest.raises(LogTemplateError):
            substitutor.substitute("{%unknown.field}", {}, scope, ctx, state, params)

    def test_underscore_prefixed_name(self, substitutor, scope, ctx, state, params) -> None:
        with pytest.raises(LogTemplateError):
            substitutor.substitute("{%var._private}", {"_private": "secret"}, scope, ctx, state, params)

    def test_missing_var_key(self, substitutor, scope, ctx, state, params) -> None:
        with pytest.raises(LogTemplateError):
            substitutor.substitute("{%var.nonexistent}", {}, scope, ctx, state, params)

    def test_unknown_color_name(self, substitutor, scope, ctx, state, params) -> None:
        with pytest.raises(LogTemplateError):
            substitutor.substitute("{%var.text|nonexistent_color}", {"text": "hello"}, scope, ctx, state, params)


class TestSubstitutorSuccess:
    """Verify successful variable substitution edge cases."""

    def test_multiple_variables(self, substitutor, scope, ctx, state, params) -> None:
        result = substitutor.substitute("{%var.a} and {%var.b}", {"a": "first", "b": "second"}, scope, ctx, state, params)
        assert "first" in result
        assert "second" in result

    def test_nested_dot_path(self, substitutor, scope, ctx, state, params) -> None:
        result = substitutor.substitute("{%var.outer.inner}", {"outer": {"inner": "deep_value"}}, scope, ctx, state, params)
        assert "deep_value" in result

    def test_color_filter_on_integer(self, substitutor, scope, ctx, state, params) -> None:
        result = substitutor.substitute("{%var.num|red}", {"num": 42}, scope, ctx, state, params)
        assert "42" in result

    def test_scope_variable(self, substitutor, scope, ctx, state, params) -> None:
        result = substitutor.substitute("{%scope.machine}", {}, scope, ctx, state, params)
        assert "TestMachine" in result

    def test_debug_filter_on_none(self, substitutor, scope, ctx, state, params) -> None:
        result = substitutor.substitute("{%var.val|debug}", {"val": None}, scope, ctx, state, params)
        assert "None" in result

    def test_debug_filter_on_empty_dict(self, substitutor, scope, ctx, state, params) -> None:
        result = substitutor.substitute("{%var.val|debug}", {"val": {}}, scope, ctx, state, params)
        assert result is not None

    def test_debug_filter_on_empty_list(self, substitutor, scope, ctx, state, params) -> None:
        result = substitutor.substitute("{%var.val|debug}", {"val": []}, scope, ctx, state, params)
        assert result is not None


class TestSubstitutorIif:
    """Verify iif expressions through the full substitute pipeline."""

    def test_iif_true_branch(self, substitutor, scope, ctx, state, params) -> None:
        result = substitutor.substitute("{iif({%var.x} > 5; 'big'; 'small')}", {"x": 10}, scope, ctx, state, params)
        assert "big" in result

    def test_iif_false_branch(self, substitutor, scope, ctx, state, params) -> None:
        result = substitutor.substitute("{iif({%var.x} > 5; 'big'; 'small')}", {"x": 2}, scope, ctx, state, params)
        assert "small" in result

    def test_iif_equality(self, substitutor, scope, ctx, state, params) -> None:
        result = substitutor.substitute("{iif({%var.status} == 'ok'; 'good'; 'bad')}", {"status": "ok"}, scope, ctx, state, params)
        assert "good" in result

    def test_iif_boolean_and(self, substitutor, scope, ctx, state, params) -> None:
        result = substitutor.substitute("{iif({%var.x} > 0 and {%var.x} < 10; 'in range'; 'out')}", {"x": 5}, scope, ctx, state, params)
        assert "in range" in result

    def test_iif_with_upper(self, substitutor, scope, ctx, state, params) -> None:
        result = substitutor.substitute("{iif({%var.x} > 0; upper('yes'); 'no')}", {"x": 5}, scope, ctx, state, params)
        assert "YES" in result

    def test_iif_arithmetic(self, substitutor, scope, ctx, state, params) -> None:
        result = substitutor.substitute("{iif({%var.x} > 0; {%var.x} + {%var.y}; 0)}", {"x": 10, "y": 20}, scope, ctx, state, params)
        assert "30" in result


class TestEvaluatorEvaluate:
    """Verify ExpressionEvaluator.evaluate() for single expressions."""

    def test_simple_comparison(self, evaluator) -> None:
        assert evaluator.evaluate("x > 10", {"x": 15}) is True

    def test_string_upper(self, evaluator) -> None:
        assert evaluator.evaluate("upper('hello')", {}) == "HELLO"

    def test_string_lower(self, evaluator) -> None:
        assert evaluator.evaluate("lower('WORLD')", {}) == "world"

    def test_len_function(self, evaluator) -> None:
        assert evaluator.evaluate("len('test')", {}) == 4

    def test_exists_true(self, evaluator) -> None:
        assert evaluator.evaluate("exists('x')", {"x": 42}) is True

    def test_exists_false(self, evaluator) -> None:
        assert evaluator.evaluate("exists('y')", {"x": 42}) is False

    def test_arithmetic(self, evaluator) -> None:
        assert evaluator.evaluate("x + y * 2", {"x": 10, "y": 5}) == 20

    def test_boolean_and(self, evaluator) -> None:
        assert evaluator.evaluate("x > 0 and x < 10", {"x": 5}) is True

    def test_boolean_or(self, evaluator) -> None:
        assert evaluator.evaluate("x > 100 or x < 0", {"x": -1}) is True

    def test_boolean_not(self, evaluator) -> None:
        assert evaluator.evaluate("not flag", {"flag": False}) is True

    def test_string_concatenation(self, evaluator) -> None:
        assert evaluator.evaluate("'hello' + ' ' + 'world'", {}) == "hello world"

    def test_undefined_variable_raises(self, evaluator) -> None:
        with pytest.raises(LogTemplateError, match="not found"):
            evaluator.evaluate("undefined_var + 1", {})

    def test_invalid_expression_raises(self, evaluator) -> None:
        """Invalid expression raises LogTemplateError."""
        with pytest.raises(LogTemplateError):
            evaluator.evaluate("def foo(): pass", {})

    def test_abs_function(self, evaluator) -> None:
        assert evaluator.evaluate("abs(-42)", {}) == 42

    def test_format_number(self, evaluator) -> None:
        result = evaluator.evaluate("format_number(1234567.891, 2)", {})
        assert "1,234,567.89" in result

    def test_debug_function(self, evaluator) -> None:
        result = evaluator.evaluate("debug({'key': 'val'})", {})
        assert "key" in result

    def test_color_function_marker(self, evaluator) -> None:
        result = evaluator.evaluate("red('error')", {})
        assert "__COLOR(red)" in result
        assert "__COLOR_END__" in result


class TestEvaluatorIif:
    """Verify ExpressionEvaluator.evaluate_iif() with semicolons."""

    def test_true_branch(self, evaluator) -> None:
        assert evaluator.evaluate_iif("x > 5; 'big'; 'small'", {"x": 10}) == "big"

    def test_false_branch(self, evaluator) -> None:
        assert evaluator.evaluate_iif("x > 5; 'big'; 'small'", {"x": 2}) == "small"

    def test_with_exists_true(self, evaluator) -> None:
        assert evaluator.evaluate_iif("exists('x'); 'found'; 'missing'", {"x": 1}) == "found"

    def test_with_exists_false(self, evaluator) -> None:
        assert evaluator.evaluate_iif("exists('y'); 'found'; 'missing'", {"x": 1}) == "missing"

    def test_with_len(self, evaluator) -> None:
        assert evaluator.evaluate_iif("len(name) > 3; 'long'; 'short'", {"name": "Alice"}) == "long"

    def test_with_upper_in_branch(self, evaluator) -> None:
        assert evaluator.evaluate_iif("1 == 1; upper('yes'); 'no'", {}) == "YES"

    def test_with_lower_in_branch(self, evaluator) -> None:
        assert evaluator.evaluate_iif("1 == 1; lower('HELLO'); 'no'", {}) == "hello"

    def test_wrong_arg_count_raises(self, evaluator) -> None:
        with pytest.raises(LogTemplateError, match="3 arguments"):
            evaluator.evaluate_iif("x > 5; 'only_two'", {"x": 10})

    def test_single_arg_raises(self, evaluator) -> None:
        with pytest.raises(LogTemplateError, match="3 arguments"):
            evaluator.evaluate_iif("x > 5", {"x": 10})

    def test_arithmetic_in_branch(self, evaluator) -> None:
        assert evaluator.evaluate_iif("x > 0; x + y; 0", {"x": 10, "y": 20}) == "30"

    def test_boolean_and_in_condition(self, evaluator) -> None:
        assert evaluator.evaluate_iif("x > 0 and x < 10; 'in range'; 'out'", {"x": 5}) == "in range"


class TestProcessTemplate:
    """Verify process_template replaces {iif(...)} in a string."""

    def test_single_iif(self, evaluator) -> None:
        result = evaluator.process_template("Status: {iif(x > 0; 'positive'; 'negative')}", {"x": 5})
        assert "positive" in result
        assert "{iif" not in result

    def test_no_iif(self, evaluator) -> None:
        assert evaluator.process_template("Hello world", {}) == "Hello world"

    def test_multiple_iifs(self, evaluator) -> None:
        result = evaluator.process_template("{iif(a > 0; 'pos'; 'neg')} and {iif(b > 0; 'pos'; 'neg')}", {"a": 1, "b": -1})
        assert "pos" in result
        assert "neg" in result


class TestIifArgSplitter:
    """Verify semicolon splitting handles strings and nested parens."""

    def test_string_with_semicolon(self, evaluator) -> None:
        result = evaluator.evaluate_iif("1 == 1; 'hello; world'; 'no'", {})
        assert result == "hello; world"

    def test_nested_parentheses(self, evaluator) -> None:
        result = evaluator.evaluate_iif("len('abc') > 2; upper('yes'); 'no'", {})
        assert result == "YES"
