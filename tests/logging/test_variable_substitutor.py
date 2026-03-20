# tests/logging/test_variable_substitutor.py
"""
Additional tests for VariableSubstitutor.

Checks:
- _quote_if_string with apostrophe inside string
"""

from action_machine.Logging.variable_substitutor import VariableSubstitutor


class TestVariableSubstitutorExtended:
    """Additional tests for VariableSubstitutor."""

    def setup_method(self):
        self.substitutor = VariableSubstitutor()

    # ------------------------------------------------------------------
    # TESTS: _quote_if_string
    # ------------------------------------------------------------------

    def test_quote_if_string_with_apostrophe(self):
        """_quote_if_string escapes single quotes inside a string."""
        result = self.substitutor._quote_if_string("it's ok")
        # Expected: 'it\'s ok'
        assert result == "'it\\'s ok'"

    def test_quote_if_string_with_quotes(self):
        """_quote_if_string escapes quotes but does not add extra."""
        result = self.substitutor._quote_if_string('hello "world"')
        assert result == '\'hello "world"\''

    def test_quote_if_string_bool(self):
        """_quote_if_string for bool returns 'True'/'False' without quotes."""
        assert self.substitutor._quote_if_string(True) == "True"
        assert self.substitutor._quote_if_string(False) == "False"

    def test_quote_if_string_number(self):
        """_quote_if_string for numbers returns string representation without quotes."""
        assert self.substitutor._quote_if_string(42) == "42"
        assert self.substitutor._quote_if_string(3.14) == "3.14"