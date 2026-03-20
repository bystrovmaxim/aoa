# tests/logging/test_color_filters.py
"""
Unit tests for color filters and error handling in logging templates.
"""

import pytest

from action_machine.Context.context import Context
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseState import BaseState
from action_machine.Core.Exceptions import LogTemplateError
from action_machine.Logging.log_scope import LogScope
from action_machine.Logging.variable_substitutor import VariableSubstitutor


class TestColorFilters:
    """Tests for color filter processing and error conditions."""

    @pytest.fixture
    def substitutor(self):
        return VariableSubstitutor()

    @pytest.fixture
    def empty_context(self):
        return Context()

    @pytest.fixture
    def empty_scope(self):
        return LogScope()

    @pytest.fixture
    def empty_state(self):
        return BaseState()

    @pytest.fixture
    def empty_params(self):
        return BaseParams()

    # ------------------------------------------------------------------
    # Tests for correct ANSI code generation
    # ------------------------------------------------------------------

    def test_foreground_color(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Simple foreground color filter should produce correct ANSI code."""
        result = substitutor.substitute(
            "{%var.text|red}",
            {"text": "hello"},
            empty_scope,
            empty_context,
            empty_state,
            empty_params
        )
        assert "\033[31mhello\033[0m" in result

    def test_background_color(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Background color filter (bg_red) should produce correct ANSI code."""
        result = substitutor.substitute(
            "{%var.text|bg_red}",
            {"text": "hello"},
            empty_scope,
            empty_context,
            empty_state,
            empty_params
        )
        assert "\033[41mhello\033[0m" in result

    def test_foreground_on_background(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Combined foreground_on_background filter."""
        result = substitutor.substitute(
            "{%var.text|red_on_blue}",
            {"text": "hello"},
            empty_scope,
            empty_context,
            empty_state,
            empty_params
        )
        assert "\033[31;44mhello\033[0m" in result

    def test_bright_colors(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Bright foreground and background colors."""
        result = substitutor.substitute(
            "{%var.text|orange_on_bright_blue}",
            {"text": "hello"},
            empty_scope,
            empty_context,
            empty_state,
            empty_params
        )
        # orange = 91, bright_blue background = 104
        assert "\033[91;104mhello\033[0m" in result

    def test_color_function_inside_iif(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Color functions inside iif should produce markers and then ANSI."""
        result = substitutor.substitute(
            "{iif(1 > 0; red('yes'); green('no'))}",
            {},
            empty_scope,
            empty_context,
            empty_state,
            empty_params
        )
        assert "\033[31myes\033[0m" in result

    def test_color_filter_outside_iif(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Color filter outside iif."""
        result = substitutor.substitute(
            "Value: {%var.x|blue}",
            {"x": 42},
            empty_scope,
            empty_context,
            empty_state,
            empty_params
        )
        assert "\033[34m42\033[0m" in result

    # ------------------------------------------------------------------
    # Tests for error conditions (LogTemplateError)
    # ------------------------------------------------------------------

    def test_unknown_foreground_color_raises(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Using an unknown color name should raise LogTemplateError."""
        with pytest.raises(LogTemplateError, match="Unknown color: 'hotpink'"):
            substitutor.substitute(
                "{%var.text|hotpink}",
                {"text": "hello"},
                empty_scope,
                empty_context,
                empty_state,
                empty_params
            )

    def test_unknown_foreground_in_combination_raises(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Unknown foreground in fg_on_bg combination."""
        with pytest.raises(LogTemplateError, match="Unknown foreground color: 'hotpink'"):
            substitutor.substitute(
                "{%var.text|hotpink_on_blue}",
                {"text": "hello"},
                empty_scope,
                empty_context,
                empty_state,
                empty_params
            )

    def test_unknown_background_in_combination_raises(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Unknown background in fg_on_bg combination."""
        with pytest.raises(LogTemplateError, match="Unknown background color: 'hotpink'"):
            substitutor.substitute(
                "{%var.text|red_on_hotpink}",
                {"text": "hello"},
                empty_scope,
                empty_context,
                empty_state,
                empty_params
            )

    def test_malformed_color_name_raises(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Color name with multiple underscores (not fg_on_bg) raises appropriate error."""
        # The current implementation will treat "red_on_blue_on_green" as fg="red", bg="blue_on_green",
        # and then complain that bg "blue_on_green" is unknown. That's acceptable.
        with pytest.raises(LogTemplateError, match="Unknown background color: 'blue_on_green'"):
            substitutor.substitute(
                "{%var.text|red_on_blue_on_green}",
                {"text": "hello"},
                empty_scope,
                empty_context,
                empty_state,
                empty_params
            )

    def test_underscore_variable_raises(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Access to a variable with underscore in the last segment raises."""
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            substitutor.substitute(
                "{%var._secret}",
                {"_secret": "value"},
                empty_scope,
                empty_context,
                empty_state,
                empty_params
            )

    def test_underscore_in_path_raises(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Access to a nested field with underscore in last segment raises."""
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            substitutor.substitute(
                "{%var.data._secret}",
                {"data": {"_secret": 123}},
                empty_scope,
                empty_context,
                empty_state,
                empty_params
            )

    def test_nonexistent_variable_raises(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Access to non-existent variable raises."""
        with pytest.raises(LogTemplateError, match="not found"):
            substitutor.substitute(
                "{%var.missing}",
                {},
                empty_scope,
                empty_context,
                empty_state,
                empty_params
            )

    def test_unknown_namespace_raises(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Unknown namespace raises."""
        with pytest.raises(LogTemplateError, match="Unknown namespace 'xxx'"):
            substitutor.substitute(
                "{%xxx.field}",
                {},
                empty_scope,
                empty_context,
                empty_state,
                empty_params
            )

    # ------------------------------------------------------------------
    # Tests for iif error propagation
    # ------------------------------------------------------------------

    def test_iif_syntax_error_raises(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Invalid iif syntax (wrong number of args) raises."""
        with pytest.raises(LogTemplateError, match="iif expects 3 arguments"):
            substitutor.substitute(
                "{iif(x > 10; 'yes')}",
                {"x": 5},
                empty_scope,
                empty_context,
                empty_state,
                empty_params
            )

    def test_iif_undefined_variable_raises(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Undefined variable inside iif raises."""
        with pytest.raises(LogTemplateError, match="Error evaluating expression"):
            substitutor.substitute(
                "{iif(missing > 10; 'yes'; 'no')}",
                {},
                empty_scope,
                empty_context,
                empty_state,
                empty_params
            )