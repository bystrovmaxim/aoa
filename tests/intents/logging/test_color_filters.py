# tests/intents/logging/test_color_filters.py
"""Tests of color filters in logging templates.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Checks the processing of color filters in logging templates. Colors are set
in two ways:

1. Filter after the variable: {%var.text|red}
2. Color function inside iif: red('text')

Colors can be simple (foreground), with a prefix bg_ (background),
or combined (foreground_on_background). 8 main ones supported
colors and their bright options.

VariableSubstitutor converts color markers to ANSI codes in the last step.
Nested markers are processed from the inside out: expanded first
the innermost marker, then the outer one.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
NESTED COLORS
═══════════════════ ════════════════════ ════════════════════ ════════════════════

With nested color functions (red('level: ' + green('ok'))) the result is
contains ANSI codes for both colors. ANSI terminal does not support nesting
colors like HTML - each RESET ( [0m) resets ALL styles. Therefore
the result looks like this:

    [31mlevel: [32mok [0m [0m

- [31m - turns on red (for "level: ")
- [32m — switches to green (for “ok”), red is lost
- [0m — reset after green
- [0m — reset after red

The tests check for correct ANSI codes in the result, not
exact nesting structure, because ANSI terminals work
like a stack machine without real nesting.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

- Simple foreground color (red, green, blue, etc.).
- Background color (bg_red, bg_blue).
- Combined color (red_on_blue, green_on_black).
- Bright options (orange, bright_green, bg_bright_red).
- Color function inside iif.
- Nested color functions inside iif.
- Errors with unknown color.
- Errors when the color name format is incorrect.
- Processing multiple colors in one message."""

import pytest

from action_machine.context.context import Context
from action_machine.logging.log_scope import LogScope
from action_machine.logging.variable_substitutor import VariableSubstitutor
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState
from action_machine.exceptions import LogTemplateError


@pytest.fixture
def substitutor() -> VariableSubstitutor:
    """A variable substitution instance."""
    return VariableSubstitutor()


@pytest.fixture
def empty_context() -> Context:
    """Empty context."""
    return Context()


@pytest.fixture
def empty_scope() -> LogScope:
    """Empty scope."""
    return LogScope()


@pytest.fixture
def empty_state() -> BaseState:
    """Empty state."""
    return BaseState()


@pytest.fixture
def empty_params() -> BaseParams:
    """Empty parameters."""
    return BaseParams()


# ======================================================================
#TESTS: Color filters (|color)
# ======================================================================


class TestColorFilters:
    """Tests of color filters in templates."""

    def test_foreground_color(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{%var.text|red} → ANSI code for red."""
        # Arrange & Act
        result = substitutor.substitute(
            "{%var.text|red}",
            {"text": "hello"},
            empty_scope, empty_context, empty_state, empty_params,
        )

        #Assert - red foreground code and reset
        assert "\033[31mhello\033[0m" in result

    def test_background_color(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{%var.text|bg_red} → red background."""
        # Arrange & Act
        result = substitutor.substitute(
            "{%var.text|bg_red}",
            {"text": "hello"},
            empty_scope, empty_context, empty_state, empty_params,
        )

        #Assert - red background code
        assert "\033[41mhello\033[0m" in result

    def test_foreground_on_background(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{%var.text|red_on_blue} → red text on a blue background."""
        # Arrange & Act
        result = substitutor.substitute(
            "{%var.text|red_on_blue}",
            {"text": "hello"},
            empty_scope, empty_context, empty_state, empty_params,
        )

        #Assert - foreground + background combination
        assert "\033[31;44mhello\033[0m" in result

    def test_bright_colors(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Bright colors: orange (91), bright_blue (94), etc."""
        # Arrange & Act
        result = substitutor.substitute(
            "{%var.text|orange_on_bright_blue}",
            {"text": "hello"},
            empty_scope, empty_context, empty_state, empty_params,
        )

        # Assert — orange = 91, bright_blue background = 104
        assert "\033[91;104mhello\033[0m" in result

    def test_multiple_colors_in_one_message(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Multiple color filters in one message."""
        # Arrange & Act
        result = substitutor.substitute(
            "{%var.a|red} and {%var.b|green}",
            {"a": "red", "b": "green"},
            empty_scope, empty_context, empty_state, empty_params,
        )

        #Assert - both colors are present
        assert "\033[31mred\033[0m" in result
        assert "\033[32mgreen\033[0m" in result

    def test_unknown_foreground_color_raises(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Unknown color → LogTemplateError."""
        # Arrange, Act & Assert
        with pytest.raises(LogTemplateError, match="Unknown color: 'hotpink'"):
            substitutor.substitute(
                "{%var.text|hotpink}",
                {"text": "hello"},
                empty_scope, empty_context, empty_state, empty_params,
            )

    def test_unknown_foreground_in_combination_raises(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Unknown foreground in combination → LogTemplateError."""
        # Arrange, Act & Assert
        with pytest.raises(LogTemplateError, match="Unknown foreground color: 'hotpink'"):
            substitutor.substitute(
                "{%var.text|hotpink_on_blue}",
                {"text": "hello"},
                empty_scope, empty_context, empty_state, empty_params,
            )

    def test_unknown_background_in_combination_raises(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Unknown background in combination → LogTemplateError."""
        # Arrange, Act & Assert
        with pytest.raises(LogTemplateError, match="Unknown background color: 'hotpink'"):
            substitutor.substitute(
                "{%var.text|red_on_hotpink}",
                {"text": "hello"},
                empty_scope, empty_context, empty_state, empty_params,
            )

    def test_malformed_color_name_raises(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Color name with multiple '_on_' (red_on_blue_on_green) →
        the part after the first '_on_' is interpreted as background,
        if background is not found → error."""
        # Arrange, Act & Assert
        with pytest.raises(LogTemplateError, match="Unknown background color: 'blue_on_green'"):
            substitutor.substitute(
                "{%var.text|red_on_blue_on_green}",
                {"text": "hello"},
                empty_scope, empty_context, empty_state, empty_params,
            )


# ======================================================================
#TESTS: Color functions inside iif
# ======================================================================


class TestColorFunctionsInIif:
    """Color functions (red('text')) inside iif."""

    def test_color_function_inside_iif(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{iif(1 > 0; red('yes'); green('no'))} → red 'yes'."""
        # Arrange & Act
        result = substitutor.substitute(
            "{iif(1 > 0; red('yes'); green('no'))}",
            {},
            empty_scope, empty_context, empty_state, empty_params,
        )

        #Assert - red code is present, green is not
        assert "\033[31myes\033[0m" in result
        assert "green" not in result

    def test_color_function_with_variable_inside_iif(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Variable inside iif passed to the color function."""
        # Arrange & Act
        result = substitutor.substitute(
            "{iif({%var.ok}; green('OK'); red('FAIL'))}",
            {"ok": True},
            empty_scope, empty_context, empty_state, empty_params,
        )

        #Assert - green OK
        assert "\033[32mOK\033[0m" in result

    def test_nested_color_functions(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Nested color functions inside iif.

        red('level: ' + green('ok')) generates nested markers.
        _apply_color_filters processes them from the inside out:
        1. green('ok') → [32mok [0m
        2. red('level: ' + ...) → [31mlevel: [32mok [0m [0m

        ANSI terminal does not support nesting - green toggles
        color from red to green, the first RESET closes green, the second - red.
        We check the presence of both ANSI codes in the result."""
        # Arrange & Act
        result = substitutor.substitute(
            "{iif(1 > 0; red('level: ' + green('ok')); 'no')}",
            {},
            empty_scope, empty_context, empty_state, empty_params,
        )

        #Assert - both ANSI codes are present
        assert "\033[31m" in result      #red opening
        assert "\033[32mok\033[0m" in result  #green with full content
        assert "level: " in result       #text between red and green


# ======================================================================
#TESTS: Combining color filters and functions
# ======================================================================


class TestCombined:
    """Mixed use of filters and functions."""

    def test_color_filter_and_function_together(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_scope: LogScope,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """Color filter outside iif and color function inside iif."""
        # Arrange & Act
        result = substitutor.substitute(
            "Static: {%var.static|blue} and {iif(1 > 0; red('dynamic'); '')}",
            {"static": "blue"},
            empty_scope, empty_context, empty_state, empty_params,
        )

        #Assert - both colors are present
        assert "\033[34mblue\033[0m" in result
        assert "\033[31mdynamic\033[0m" in result
        assert "\033[31mdynamic\033[0m" in result
