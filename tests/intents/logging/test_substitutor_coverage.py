# tests/intents/logging/test_substitutor_coverage.py
"""Targeted coverage tests for VariableSubstitutor.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Closes uncovered lines in variable_substitutor.py [4]:

- Navigation through BaseSchema via DotPathNavigator [2].
- Navigation by regular dict (key not found).
- Navigation via getattr for arbitrary objects.
- _get_property_config - @sensitive detection [1].
- _quote_if_string — formatting of color markers.
- _format_variable_for_template — inside_iif branches
  for bool, int, string.
- _substitute_with_iif_detection - variables
  inside and outside iif blocks at the same time.
- _substitute_variables - fast/slow path manager.
- _resolve_color_name - bg_ branch (background only).
- _resolve_color_name - fg_on_bg branch (foreground + background).

═══════════════════ ════════════════════ ════════════════════ ════════════════════
ORGANIZATION
═══════════════════ ════════════════════ ════════════════════ ════════════════════

- TestQuoteIfString - static _quote_if_string method for all types.
- TestResolveColorName - all three color name formats and errors.
- TestIifWithMixedVariables - templates with variables simultaneously inside
  and outside {iif(...)}.
- TestNamespaceResolution — state, params, context namespace.
- TestDebugInsideIifTemplate - debug filter next to iif.
- TestNavigationSteps - navigation via DotPathNavigator for BaseSchema,
  dict, arbitrary objects."""

import pytest

from action_machine.context.context import Context
from action_machine.logging.log_scope import LogScope
from action_machine.logging.variable_substitutor import VariableSubstitutor
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState
from action_machine.exceptions import LogTemplateError
from action_machine.testing.stubs import ContextStub
from tests.scenarios.domain_model import SimpleAction

# ─────────────────────────────────────────────────────────────────────────────
#General fittings
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def sub() -> VariableSubstitutor:
    """A fresh instance of VariableSubstitutor."""
    return VariableSubstitutor()


@pytest.fixture()
def scope() -> LogScope:
    """Minimum LogScope for substitution tests."""
    return LogScope(machine="M", mode="test", action="A", aspect="a", nest_level=0)


@pytest.fixture()
def ctx() -> Context:
    """Minimum Context for substitution tests."""
    return Context()


@pytest.fixture()
def state() -> BaseState:
    """Empty BaseState for substitution tests."""
    return BaseState()


@pytest.fixture()
def params() -> BaseParams:
    """Empty BaseParams for substitution tests."""
    return BaseParams()


# ═════════════════════════════════════════════════════════════════════════════
#_quote_if_string - formatting literals for simpleeval
# ═════════════════════════════════════════════════════════════════════════════

class TestQuoteIfString:
    """Covers _quote_if_string for all value types."""

    def test_boolean_true_not_quoted(self) -> None:
        """True is returned as the string 'True' without quotes."""
        # Arrange / Act
        result = VariableSubstitutor._quote_if_string(True)

        #Assert - boolean values ​​are not wrapped in quotes
        assert result == "True"

    def test_boolean_false_not_quoted(self) -> None:
        """False is returned as the string 'False' without quotes."""
        # Arrange / Act
        result = VariableSubstitutor._quote_if_string(False)

        # Assert
        assert result == "False"

    def test_integer_not_quoted(self) -> None:
        """The integer is returned as a string without quotes."""
        # Arrange / Act
        result = VariableSubstitutor._quote_if_string(42)

        # Assert
        assert result == "42"

    def test_float_not_quoted(self) -> None:
        """The fractional number is returned as a string without quotes."""
        # Arrange / Act
        result = VariableSubstitutor._quote_if_string(3.14)

        # Assert
        assert result == "3.14"

    def test_plain_string_quoted(self) -> None:
        """A regular string is wrapped in single quotes."""
        # Arrange / Act
        result = VariableSubstitutor._quote_if_string("hello")

        # Assert
        assert result == "'hello'"

    def test_string_with_single_quote_escaped(self) -> None:
        """A string with a single quote inside - the quote is escaped."""
        # Arrange / Act
        result = VariableSubstitutor._quote_if_string("it's")

        #Assert - the inner quote is escaped
        assert "\\'" in result

    def test_color_marker_not_quoted(self) -> None:
        """The color marker is returned without quotes to save the marker."""
        #Arrange - the line contains __COLOR(...)...__COLOR_END__
        marker = "__COLOR(red)error__COLOR_END__"

        # Act
        result = VariableSubstitutor._quote_if_string(marker)

        #Assert - the token is returned as is, without wrapping in quotes
        assert result == marker


# ═════════════════════════════════════════════════════════════════════════════
#_resolve_color_name - all three color name formats
# ═════════════════════════════════════════════════════════════════════════════

class TestResolveColorName:
    """Covers _resolve_color_name: fg, bg_, fg_on_bg and errors."""

    def test_simple_foreground(self, sub) -> None:
        """A simple color name returns foreground ANSI code."""
        # Arrange / Act
        result = sub._resolve_color_name("green")

        #Assert - green = ANSI code 32
        assert result == "\033[32m"

    def test_background_color(self, sub) -> None:
        """A name prefixed with bg_ returns background ANSI code."""
        # Arrange / Act
        result = sub._resolve_color_name("bg_red")

        #Assert - bg_red = ANSI code 41
        assert result == "\033[41m"

    def test_foreground_on_background(self, sub) -> None:
        """The fg_on_bg format returns a combined ANSI code."""
        # Arrange / Act
        result = sub._resolve_color_name("red_on_blue")

        # Assert — red=31, blue=44
        assert result == "\033[31;44m"

    def test_unknown_foreground_raises(self, sub) -> None:
        """Unknown foreground name raises LogTemplateError."""
        # Arrange / Act / Assert
        with pytest.raises(LogTemplateError, match="color"):
            sub._resolve_color_name("rainbow")

    def test_unknown_background_alone_raises(self, sub) -> None:
        """Unknown name bg_ raises LogTemplateError."""
        # Arrange / Act / Assert
        with pytest.raises(LogTemplateError, match="background"):
            sub._resolve_color_name("bg_rainbow")

    def test_unknown_fg_in_combo_raises(self, sub) -> None:
        """An unknown foreground in fg_on_bg causes a LogTemplateError."""
        # Arrange / Act / Assert
        with pytest.raises(LogTemplateError, match="foreground"):
            sub._resolve_color_name("fakefg_on_blue")

    def test_unknown_bg_in_combo_raises(self, sub) -> None:
        """Unknown background in fg_on_bg raises LogTemplateError."""
        # Arrange / Act / Assert
        with pytest.raises(LogTemplateError, match="background"):
            sub._resolve_color_name("red_on_fakebg")


# ═════════════════════════════════════════════════════════════════════════════
#Variables are both inside and outside {iif(...)}
# ═════════════════════════════════════════════════════════════════════════════

class TestIifWithMixedVariables:
    """Covers _substitute_with_iif_detection - the slow way."""

    def test_var_outside_and_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """The variable outside iif is a plain string, inside iif is a literal."""
        #Arrange - template contains {%var.label} outside and {%var.x} inside iif
        template = "Label: {%var.label} Result: {iif({%var.x} > 0; 'pos'; 'neg')}"

        # Act
        result = sub.substitute(template, {"label": "test", "x": 5}, scope, ctx, state, params)

        #Assert - both substitutions were performed correctly
        assert "Label: test" in result
        assert "pos" in result

    def test_boolean_var_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """A boolean variable inside iif is formatted without quotes."""
        #Arrange — flag=True → substituted as True (without quotes)
        template = "{iif({%var.flag}; 'yes'; 'no')}"

        # Act
        result = sub.substitute(template, {"flag": True}, scope, ctx, state, params)

        # Assert
        assert "yes" in result

    def test_integer_var_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """An integer variable inside iif is formatted without quotes."""
        #Arrange — count=3 → substituted as 3 (a number, not the string '3')
        template = "{iif({%var.count} > 0; 'some'; 'none')}"

        # Act
        result = sub.substitute(template, {"count": 3}, scope, ctx, state, params)

        # Assert
        assert "some" in result

    def test_string_var_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """A string variable inside iif is wrapped in quotes."""
        #Arrange — status='ok' → substituted as 'ok' (with quotes)
        template = "{iif({%var.status} == 'ok'; 'good'; 'bad')}"

        # Act
        result = sub.substitute(template, {"status": "ok"}, scope, ctx, state, params)

        # Assert
        assert "good" in result

    def test_multiple_vars_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """Several variables within one iif."""
        #Arrange - both variables inside iif
        template = "{iif({%var.x} + {%var.y} > 10; 'big'; 'small')}"

        # Act
        result = sub.substitute(template, {"x": 7, "y": 5}, scope, ctx, state, params)

        # Assert
        assert "big" in result


# ═════════════════════════════════════════════════════════════════════════════
#Resolution namespace: state, params, context
# ═════════════════════════════════════════════════════════════════════════════

class TestNamespaceResolution:
    """Covers resolvers for state, params, context namespace."""

    def test_state_variable(self, sub, scope, ctx, params) -> None:
        """Namespace state resolves values ​​from BaseState."""
        #Arrange - state contains txn_id
        st = BaseState(txn_id="TXN-001")

        # Act
        result = sub.substitute("{%state.txn_id}", {}, scope, ctx, st, params)

        # Assert
        assert "TXN-001" in result

    def test_params_variable(self, sub, scope, ctx, state) -> None:
        """Namespace params resolves values ​​from Params fields."""
        #Arrange - SimpleAction.Params has a name field
        p = SimpleAction.Params(name="Alice")

        # Act
        result = sub.substitute("{%params.name}", {}, scope, ctx, state, p)

        # Assert
        assert "Alice" in result

    def test_context_nested_variable(self, sub, scope, state, params) -> None:
        """Namespace context allows nested fields via dot-path."""
        #Arrange - ContextStub contains user.user_id
        c = ContextStub()

        # Act
        result = sub.substitute("{%context.user.user_id}", {}, scope, c, state, params)

        # Assert
        assert "test_user" in result

    def test_scope_nested_variable(self, sub, ctx, state, params) -> None:
        """Namespace scope allows LogScope fields [3]."""
        #Arrange — LogScope contains action
        sc = LogScope(machine="M", mode="test", action="MyAction", aspect="a", nest_level=0)

        # Act
        result = sub.substitute("{%scope.action}", {}, sc, ctx, state, params)

        # Assert
        assert "MyAction" in result


# ═════════════════════════════════════════════════════════════════════════════
#Debug filter next to iif in one template
# ═════════════════════════════════════════════════════════════════════════════

class TestDebugInsideIifTemplate:
    """Covers a pattern with |debug and {iif(...)} at the same time."""

    def test_debug_and_iif_together(self, sub, scope, ctx, state, params) -> None:
        """Debug filter and iif in one template are both processed correctly."""
        #Arrange - |debug outside iif, {iif} with numeric condition
        template = "{%var.obj|debug} - {iif({%var.x} > 0; 'ok'; 'fail')}"

        # Act
        result = sub.substitute(
            template,
            {"obj": {"key": "val"}, "x": 1},
            scope, ctx, state, params,
        )

        #Assert — debug output the contents of the object, iif returned 'ok'
        assert "key" in result
        assert "ok" in result


# ═════════════════════════════════════════════════════════════════════════════
#Navigation - DotPathNavigator for different types of objects
# ═════════════════════════════════════════════════════════════════════════════

class TestNavigationSteps:
    """Covers navigation via DotPathNavigator for BaseSchema, dict, generic."""

    def test_dict_navigation(self, sub, scope, ctx, state, params) -> None:
        """Nested dict navigation via dot-path."""
        #Arrange - three-level nested dict
        template = "{%var.a.b.c}"
        var = {"a": {"b": {"c": "deep"}}}

        # Act
        result = sub.substitute(template, var, scope, ctx, state, params)

        # Assert
        assert "deep" in result

    def test_object_navigation_via_getattr(self, sub, scope, ctx, state, params) -> None:
        """Navigation through object attributes via getattr."""
        #Arrange - context.user is an object with a user_id attribute
        c = ContextStub()

        # Act
        result = sub.substitute("{%context.user.user_id}", {}, scope, c, state, params)

        # Assert
        assert "test_user" in result

    def test_state_navigation(self, sub, scope, ctx, params) -> None:
        """Navigation through BaseState (BaseSchema) via __getitem__ [2]."""
        #Arrange - BaseState supports __getitem__
        st = BaseState(nested={"key": "value"})

        # Act
        result = sub.substitute("{%state.nested.key}", {}, scope, ctx, st, params)

        # Assert
        assert "value" in result

    def test_missing_intermediate_key(self, sub, scope, ctx, state, params) -> None:
        """Missing intermediate key in dot-path → LogTemplateError."""
        #Arrange - var.a exists, but var.a.missing does not
        template = "{%var.a.missing.deep}"

        # Act / Assert
        with pytest.raises(LogTemplateError):
            sub.substitute(template, {"a": {"other": 1}}, scope, ctx, state, params)
            sub.substitute(template, {"a": {"other": 1}}, scope, ctx, state, params)
