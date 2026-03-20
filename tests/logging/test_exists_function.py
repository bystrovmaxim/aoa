# tests/logging/test_exists_function.py
"""
Unit tests for the exists() function in logging templates.

The exists(name) function returns True if a variable with the given name
exists in the current evaluation context, otherwise False.
It can be used inside iif to safely check for variable presence.
"""

import pytest

from action_machine.Logging.expression_evaluator import ExpressionEvaluator


class TestExistsFunction:
    """Tests for the exists() function."""

    @pytest.fixture
    def evaluator(self):
        return ExpressionEvaluator()

    # ------------------------------------------------------------------
    # Basic exists tests
    # ------------------------------------------------------------------

    def test_exists_true(self, evaluator: ExpressionEvaluator):
        """exists returns True for an existing variable."""
        result = evaluator.evaluate("exists('var.amount')", {"var.amount": 1500})
        assert result is True

    def test_exists_false(self, evaluator: ExpressionEvaluator):
        """exists returns False for a missing variable."""
        result = evaluator.evaluate("exists('var.missing')", {"var.amount": 1500})
        assert result is False

    def test_exists_with_dot_in_name(self, evaluator: ExpressionEvaluator):
        """exists works with dot‑separated names (string literal)."""
        result = evaluator.evaluate("exists('var.user.name')", {"var.user.name": "Alice"})
        assert result is True

        result = evaluator.evaluate("exists('var.user.name')", {})
        assert result is False

    def test_exists_with_quoted_string(self, evaluator: ExpressionEvaluator):
        """exists expects a string literal argument."""
        result = evaluator.evaluate("exists('var.data')", {"var.data": 123})
        assert result is True

        result = evaluator.evaluate('exists("var.data")', {"var.data": 123})
        assert result is True

    # ------------------------------------------------------------------
    # exists inside iif
    # ------------------------------------------------------------------

    def test_exists_in_iif_true_branch(self, evaluator: ExpressionEvaluator):
        """exists in iif condition returns True, the true branch is executed."""
        names = {"var.amount": 1500}
        template = "{iif(exists('var.amount'); 'Has amount'; 'No amount')}"
        result = evaluator.process_template(template, names)
        assert result == "Has amount"

    def test_exists_in_iif_false_branch(self, evaluator: ExpressionEvaluator):
        """exists in iif condition returns False, the false branch is executed."""
        names = {}
        template = "{iif(exists('var.amount'); 'Has amount'; 'No amount')}"
        result = evaluator.process_template(template, names)
        assert result == "No amount"

    def test_exists_with_complex_variable(self, evaluator: ExpressionEvaluator):
        """exists can check for deeply nested variables."""
        names = {"var.user.profile.age": 30}
        template = "{iif(exists('var.user.profile.age'); 'Has age'; 'No age')}"
        result = evaluator.process_template(template, names)
        assert result == "Has age"

        result = evaluator.process_template(template, {})
        assert result == "No age"

    # ------------------------------------------------------------------
    # exists combined with debug to avoid errors
    # ------------------------------------------------------------------

    def test_exists_with_debug(self, evaluator: ExpressionEvaluator):
        """exists can be used with debug to safely introspect optional objects."""
        class DataObj:
            def __init__(self):
                self.a = 1
        names = {"data": DataObj()}
        template = "{iif(exists('data'); debug(data); 'No data')}"
        result = evaluator.process_template(template, names)
        assert "a: int = 1" in result

        result = evaluator.process_template(template, {})
        assert result == "No data"

    def test_exists_with_nested_variable_and_debug(self, evaluator: ExpressionEvaluator):
        """exists checks for the existence of the whole path."""
        class Profile:
            def __init__(self):
                self.age = 30
        profile_obj = Profile()
        names = {"profile": profile_obj}
        template = "{iif(exists('profile'); debug(profile); 'No profile')}"
        result = evaluator.process_template(template, names)
        assert "age: int = 30" in result

        result = evaluator.process_template(template, {})
        assert result == "No profile"

    # ------------------------------------------------------------------
    # exists as a standalone expression (not inside iif)
    # ------------------------------------------------------------------

    def test_exists_standalone(self, evaluator: ExpressionEvaluator):
        """exists can be used as a standalone expression."""
        result = evaluator.evaluate("exists('var.amount')", {"var.amount": 10})
        assert result is True

        result = evaluator.evaluate("exists('var.amount')", {})
        assert result is False

    def test_exists_standalone_with_iif_template(self, evaluator: ExpressionEvaluator):
        """Standalone exists should be wrapped in iif to work in templates."""
        names = {"var.amount": 10}
        template = "{iif(exists('var.amount'); 'True'; 'False')}"
        result = evaluator.process_template(template, names)
        assert result == "True"

        result = evaluator.process_template(template, {})
        assert result == "False"

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_exists_with_empty_string_name(self, evaluator: ExpressionEvaluator):
        """exists with empty string returns False (no such variable)."""
        result = evaluator.evaluate("exists('')", {})
        assert result is False

    def test_exists_with_non_string_argument_raises(self, evaluator: ExpressionEvaluator):
        """exists with a non-string argument should return False (no exception)."""
        result = evaluator.evaluate("exists(123)", {})
        assert result is False

    def test_exists_does_not_evaluate_variable(self, evaluator: ExpressionEvaluator):
        """exists checks name existence without evaluating the variable."""
        result = evaluator.evaluate("exists('var.circular')", {"var.circular": object()})
        assert result is True