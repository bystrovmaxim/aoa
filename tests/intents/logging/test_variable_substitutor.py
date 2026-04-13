# tests/intents/logging/test_variable_substitutor.py
"""Full tests of VariableSubstitutor - an engine for substituting variables in templates.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Covers all aspects of the VariableSubstitutor [4]:

- Resolution of variables from five namespaces: var, state, scope, context, params.
- Navigation through nested objects via DotPathNavigator.
- Protection against access to private attributes (check '_' in all segments).
- Formatting literals for simpleeval (_quote_if_string).
- Two-pass substitution: variables → iif.
- Color filters (|color) and color functions inside iif.
- Debug filter (|debug).
- Masking @sensitive properties.
- Strict error handling: LogTemplateError for all invalid cases.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
ORGANIZATION
═══════════════════ ════════════════════ ════════════════════ ════════════════════

- TestValidatePathSegments - static method _validate_path_segments.
- TestUnderscoreSecurityAllPaths - attack vectors through '_' segments.
- TestNamespaceResolution - resolution from var, state, scope, context, params.
- TestNestedNavigation - navigation through DotPathNavigator for different types.
- TestQuoteIfString - formatting literals for simpleeval.
- TestResolveColorName - three color and error name formats.
- TestColorFilters - post-processing of color markers → ANSI.
- TestDebugFilter - filter |debug outside and near iif.
- TestSensitiveMasking - masking @sensitive properties.
- TestIifSubstitution - variables inside and outside {iif(...)}.
- TestSubstitutePublicAPI - full cycle via substitute().
- TestErrorHandling - all LogTemplateError scenarios."""

import pytest

from action_machine.intents.context.context import Context
from action_machine.intents.logging.log_scope import LogScope
from action_machine.intents.logging.variable_substitutor import VariableSubstitutor
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState
from action_machine.model.exceptions import LogTemplateError
from action_machine.testing.stubs import ContextStub
from tests.scenarios.domain_model import SimpleAction

# ─────────────────────────────────────────────────────────────────────────────
#Auxiliary models for tests
# ─────────────────────────────────────────────────────────────────────────────

class _SensitiveUser:
    """An object with a @sensitive property for masking tests."""

    def __init__(self, token: str) -> None:
        self._token = token

    @property
    def token(self) -> str:
        return self._token

    #Imitating the @sensitive decorator - hanging _sensitive_config on the getter
    token.fget._sensitive_config = {  # type: ignore[attr-defined]
        "enabled": True,
        "max_chars": 3,
        "char": "*",
        "max_percent": 50,
    }


class _SensitiveDisabledUser:
    """Object with @sensitive(enabled=False) for disabled masking tests."""

    def __init__(self, token: str) -> None:
        self._token = token

    @property
    def token(self) -> str:
        return self._token

    token.fget._sensitive_config = {  # type: ignore[attr-defined]
        "enabled": False,
        "max_chars": 3,
        "char": "*",
        "max_percent": 50,
    }


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
    return LogScope(machine="TestMachine", mode="test", action="TestAction", aspect="test_aspect", nest_level=0)


@pytest.fixture()
def ctx() -> Context:
    """Context with test user."""
    return ContextStub()


@pytest.fixture()
def state() -> BaseState:
    """Empty BaseState."""
    return BaseState()


@pytest.fixture()
def params() -> BaseParams:
    """Empty BaseParams."""
    return BaseParams()


# ═════════════════════════════════════════════════════════════════════════════
#_validate_path_segments - checks all segments for '_'
# ═════════════════════════════════════════════════════════════════════════════

class TestValidatePathSegments:
    """Validate _validate_path_segments for all segment positions."""

    def test_normal_path_passes(self) -> None:
        """The usual way without underscores - the check passes."""
        #Act/Assert - should not throw an exception
        VariableSubstitutor._validate_path_segments("context", "user.user_id")

    def test_single_segment_passes(self) -> None:
        """A single segment without an underline—the test passes."""
        VariableSubstitutor._validate_path_segments("var", "amount")

    def test_underscore_first_segment_blocked(self) -> None:
        """Underscore in the first segment → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="_internal"):
            VariableSubstitutor._validate_path_segments("context", "_internal.public_key")

    def test_underscore_middle_segment_blocked(self) -> None:
        """Underscore in intermediate segment → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="_private"):
            VariableSubstitutor._validate_path_segments("context", "user._private.name")

    def test_underscore_last_segment_blocked(self) -> None:
        """Underscore in the last segment → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="_secret"):
            VariableSubstitutor._validate_path_segments("context", "user._secret")

    def test_dunder_segment_blocked(self) -> None:
        """Dunder attribute (__dict__) → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="__dict__"):
            VariableSubstitutor._validate_path_segments("context", "__dict__.keys")

    def test_dunder_chain_blocked(self) -> None:
        """The chain of dunder attributes → is blocked at the first one."""
        with pytest.raises(LogTemplateError, match="__class__"):
            VariableSubstitutor._validate_path_segments("context", "__class__.__name__")


# ═════════════════════════════════════════════════════════════════════════════
#Security - attacks via intermediate '_' segments
# ═════════════════════════════════════════════════════════════════════════════

class TestUnderscoreSecurityAllPaths:
    """Checking for underscore blocking through a full substitute() loop."""

    def test_underscore_in_first_segment_via_substitute(self, sub, scope, ctx, state, params) -> None:
        """The template {%context._internal.public} is blocked."""
        with pytest.raises(LogTemplateError, match="underscore"):
            sub.substitute("{%context._internal.public}", {}, scope, ctx, state, params)

    def test_underscore_in_middle_segment_via_substitute(self, sub, scope, ctx, state, params) -> None:
        """The template {%var.obj._hidden.value} is blocked."""
        with pytest.raises(LogTemplateError, match="underscore"):
            sub.substitute("{%var.obj._hidden.value}", {"obj": {"_hidden": {"value": 1}}}, scope, ctx, state, params)

    def test_dunder_via_substitute(self, sub, scope, ctx, state, params) -> None:
        """The template {%context.__dict__.keys} is blocked."""
        with pytest.raises(LogTemplateError, match="underscore"):
            sub.substitute("{%context.__dict__.keys}", {}, scope, ctx, state, params)

    def test_last_segment_underscore_still_blocked(self, sub, scope, ctx, state, params) -> None:
        """Template {%var._secret} is blocked (last segment)."""
        with pytest.raises(LogTemplateError, match="underscore"):
            sub.substitute("{%var._secret}", {"_secret": "hidden"}, scope, ctx, state, params)

    def test_underscore_in_iif_blocked(self, sub, scope, ctx, state, params) -> None:
        """Underscores inside iif are also blocked."""
        with pytest.raises(LogTemplateError, match="underscore"):
            sub.substitute(
                "{iif({%var._flag}; 'yes'; 'no')}",
                {"_flag": True},
                scope, ctx, state, params,
            )


# ═════════════════════════════════════════════════════════════════════════════
#Namespace resolution: var, state, scope, context, params
# ═════════════════════════════════════════════════════════════════════════════

class TestNamespaceResolution:
    """Resolving variables from all five namespaces."""

    def test_var_simple(self, sub, scope, ctx, state, params) -> None:
        """Namespace var is a simple dictionary variable."""
        result = sub.substitute("{%var.amount}", {"amount": 100}, scope, ctx, state, params)
        assert "100" in result

    def test_var_nested_dict(self, sub, scope, ctx, state, params) -> None:
        """Namespace var - nested dict via dot-path."""
        result = sub.substitute("{%var.a.b.c}", {"a": {"b": {"c": "deep"}}}, scope, ctx, state, params)
        assert "deep" in result

    def test_state_variable(self, sub, scope, ctx, params) -> None:
        """Namespace state - value from BaseState [2]."""
        st = BaseState(txn_id="TXN-001")
        result = sub.substitute("{%state.txn_id}", {}, scope, ctx, st, params)
        assert "TXN-001" in result

    def test_scope_variable(self, sub, ctx, state, params) -> None:
        """Namespace scope - field from LogScope [3]."""
        sc = LogScope(machine="M", mode="test", action="MyAction", aspect="a", nest_level=0)
        result = sub.substitute("{%scope.action}", {}, sc, ctx, state, params)
        assert "MyAction" in result

    def test_context_nested_variable(self, sub, scope, state, params) -> None:
        """Namespace context - nested fields via dot-path [2]."""
        c = ContextStub()
        result = sub.substitute("{%context.user.user_id}", {}, scope, c, state, params)
        assert "test_user" in result

    def test_params_variable(self, sub, scope, ctx, state) -> None:
        """Namespace params - field from BaseParams [9]."""
        p = SimpleAction.Params(name="Alice")
        result = sub.substitute("{%params.name}", {}, scope, ctx, state, p)
        assert "Alice" in result

    def test_unknown_namespace_raises(self, sub, scope, ctx, state, params) -> None:
        """Unknown namespace -> LogTemplateError."""
        with pytest.raises(LogTemplateError, match="Unknown namespace"):
            sub.substitute("{%unknown.field}", {}, scope, ctx, state, params)


# ═════════════════════════════════════════════════════════════════════════════
#Navigate through nested objects
# ═════════════════════════════════════════════════════════════════════════════

class TestNestedNavigation:
    """Navigation via DotPathNavigator for different types of objects."""

    def test_dict_three_levels(self, sub, scope, ctx, state, params) -> None:
        """Three-level nested dict."""
        var = {"a": {"b": {"c": 42}}}
        result = sub.substitute("{%var.a.b.c}", var, scope, ctx, state, params)
        assert "42" in result

    def test_schema_nested(self, sub, scope, state, params) -> None:
        """Navigation through nested BaseSchema objects [2]."""
        c = ContextStub()
        result = sub.substitute("{%context.user.user_id}", {}, scope, c, state, params)
        assert "test_user" in result

    def test_state_with_nested_dict(self, sub, scope, ctx, params) -> None:
        """BaseState with nested dict."""
        st = BaseState(nested={"key": "value"})
        result = sub.substitute("{%state.nested.key}", {}, scope, ctx, st, params)
        assert "value" in result

    def test_missing_variable_raises(self, sub, scope, ctx, state, params) -> None:
        """Non-existent variable → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="not found"):
            sub.substitute("{%var.missing}", {}, scope, ctx, state, params)

    def test_missing_intermediate_key_raises(self, sub, scope, ctx, state, params) -> None:
        """Missing intermediate key → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="not found"):
            sub.substitute("{%var.a.missing.deep}", {"a": {"other": 1}}, scope, ctx, state, params)


# ═════════════════════════════════════════════════════════════════════════════
#_quote_if_string - formatting literals for simpleeval
# ═════════════════════════════════════════════════════════════════════════════

class TestQuoteIfString:
    """Formatting values ​​for substitution within iif [11]."""

    def test_boolean_true(self) -> None:
        """True → 'True' without quotes."""
        assert VariableSubstitutor._quote_if_string(True) == "True"

    def test_boolean_false(self) -> None:
        """False → 'False' without quotes."""
        assert VariableSubstitutor._quote_if_string(False) == "False"

    def test_integer(self) -> None:
        """Integer -> string without quotes."""
        assert VariableSubstitutor._quote_if_string(42) == "42"

    def test_float(self) -> None:
        """Fractional number → string without quotes."""
        assert VariableSubstitutor._quote_if_string(3.14) == "3.14"

    def test_plain_string(self) -> None:
        """Regular string → in single quotes."""
        assert VariableSubstitutor._quote_if_string("hello") == "'hello'"

    def test_string_with_single_quote(self) -> None:
        """The quoted string → is escaped."""
        result = VariableSubstitutor._quote_if_string("it's")
        assert "\\'" in result

    def test_color_marker_not_quoted(self) -> None:
        """Color marker → without quotes."""
        marker = "__COLOR(red)error__COLOR_END__"
        assert VariableSubstitutor._quote_if_string(marker) == marker


# ═════════════════════════════════════════════════════════════════════════════
#_resolve_color_name - three color formats
# ═════════════════════════════════════════════════════════════════════════════

class TestResolveColorName:
    """Convert color name to ANSI code."""

    def test_simple_foreground(self, sub) -> None:
        """Simple foreground: green → ANSI 32."""
        assert sub._resolve_color_name("green") == "\033[32m"

    def test_background(self, sub) -> None:
        """Background with bg_ prefix: bg_red → ANSI 41."""
        assert sub._resolve_color_name("bg_red") == "\033[41m"

    def test_fg_on_bg(self, sub) -> None:
        """Combination fg_on_bg: red_on_blue → ANSI 31;44."""
        assert sub._resolve_color_name("red_on_blue") == "\033[31;44m"

    def test_unknown_foreground_raises(self, sub) -> None:
        """Unknown foreground -> LogTemplateError."""
        with pytest.raises(LogTemplateError, match="color"):
            sub._resolve_color_name("rainbow")

    def test_unknown_background_raises(self, sub) -> None:
        """Unknown bg_ -> LogTemplateError."""
        with pytest.raises(LogTemplateError, match="background"):
            sub._resolve_color_name("bg_rainbow")

    def test_unknown_fg_in_combo_raises(self, sub) -> None:
        """Unknown fg in fg_on_bg → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="foreground"):
            sub._resolve_color_name("fakefg_on_blue")

    def test_unknown_bg_in_combo_raises(self, sub) -> None:
        """Unknown bg in fg_on_bg -> LogTemplateError."""
        with pytest.raises(LogTemplateError, match="background"):
            sub._resolve_color_name("red_on_fakebg")


# ═════════════════════════════════════════════════════════════════════════════
#Color filters - |color and marker post-processing
# ═════════════════════════════════════════════════════════════════════════════

class TestColorFilters:
    """Color filters via |color and replacing markers with ANSI."""

    def test_color_filter_produces_ansi(self, sub, scope, ctx, state, params) -> None:
        """The |red filter wraps the value in ANSI red."""
        result = sub.substitute("{%var.msg|red}", {"msg": "error"}, scope, ctx, state, params)
        assert "\033[31m" in result
        assert "error" in result
        assert "\033[0m" in result

    def test_color_filter_green(self, sub, scope, ctx, state, params) -> None:
        """The |green filter wraps the value in ANSI green."""
        result = sub.substitute("{%var.msg|green}", {"msg": "ok"}, scope, ctx, state, params)
        assert "\033[32m" in result

    def test_nested_color_markers(self, sub) -> None:
        """Nested color markers are processed from the inside out."""
        text = "__COLOR(red)outer __COLOR(green)inner__COLOR_END__ end__COLOR_END__"
        result = sub._apply_color_filters(text)
        assert "\033[31m" in result
        assert "\033[32m" in result
        assert "__COLOR" not in result

    def test_no_markers_unchanged(self, sub) -> None:
        """A string without tokens is returned unchanged."""
        text = "plain text without colors"
        assert sub._apply_color_filters(text) == text


# ═════════════════════════════════════════════════════════════════════════════
#Debug filter - |debug
# ═════════════════════════════════════════════════════════════════════════════

class TestDebugFilter:
    """The |debug filter outputs an introspection of an object [11]."""

    def test_debug_dict(self, sub, scope, ctx, state, params) -> None:
        """Debug for dict outputs keys and values."""
        result = sub.substitute("{%var.obj|debug}", {"obj": {"key": "val"}}, scope, ctx, state, params)
        assert "key" in result

    def test_debug_with_iif(self, sub, scope, ctx, state, params) -> None:
        """Debug and iif in the same template both work."""
        template = "{%var.obj|debug} - {iif({%var.x} > 0; 'ok'; 'fail')}"
        result = sub.substitute(template, {"obj": {"k": "v"}, "x": 1}, scope, ctx, state, params)
        assert "k" in result
        assert "ok" in result

    def test_debug_simple_value(self, sub, scope, ctx, state, params) -> None:
        """Debug for a simple value (string)."""
        result = sub.substitute("{%var.name|debug}", {"name": "Alice"}, scope, ctx, state, params)
        assert "Alice" in result


# ═════════════════════════════════════════════════════════════════════════════
#Masking @sensitive properties
# ═════════════════════════════════════════════════════════════════════════════

class TestSensitiveMasking:
    """Masking property values ​​with @sensitive [12]."""

    def test_sensitive_property_masked(self, sub, scope, ctx, state, params) -> None:
        """A property with @sensitive is masked in the output."""
        user = _SensitiveUser(token="super_secret_token_123")
        result = sub.substitute("{%var.user.token}", {"user": user}, scope, ctx, state, params)
        #The value is masked - the full token is not visible
        assert "super_secret_token_123" not in result
        assert "*" in result

    def test_sensitive_disabled_not_masked(self, sub, scope, ctx, state, params) -> None:
        """A property with @sensitive(enabled=False) is not masked."""
        user = _SensitiveDisabledUser(token="visible_token")
        result = sub.substitute("{%var.user.token}", {"user": user}, scope, ctx, state, params)
        assert "visible_token" in result

    def test_regular_attribute_not_masked(self, sub, scope, ctx, state, params) -> None:
        """A regular attribute (without @sensitive) is not masked."""
        result = sub.substitute("{%var.name}", {"name": "Alice"}, scope, ctx, state, params)
        assert result == "Alice"


# ═════════════════════════════════════════════════════════════════════════════
#iif - variables inside and outside {iif(...)}
# ═════════════════════════════════════════════════════════════════════════════

class TestIifSubstitution:
    """Two-pass substitution: variables → iif [11]."""

    def test_var_outside_and_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """The variable outside iif is plain, inside iif is a literal."""
        template = "Label: {%var.label} Result: {iif({%var.x} > 0; 'pos'; 'neg')}"
        result = sub.substitute(template, {"label": "test", "x": 5}, scope, ctx, state, params)
        assert "Label: test" in result
        assert "pos" in result

    def test_boolean_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """Boolean variable inside iif - without quotes."""
        result = sub.substitute("{iif({%var.flag}; 'yes'; 'no')}", {"flag": True}, scope, ctx, state, params)
        assert "yes" in result

    def test_integer_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """Integer inside iif - without quotes."""
        result = sub.substitute("{iif({%var.count} > 0; 'some'; 'none')}", {"count": 3}, scope, ctx, state, params)
        assert "some" in result

    def test_string_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """The string inside iif is in quotes."""
        result = sub.substitute("{iif({%var.status} == 'ok'; 'good'; 'bad')}", {"status": "ok"}, scope, ctx, state, params)
        assert "good" in result

    def test_multiple_vars_inside_iif(self, sub, scope, ctx, state, params) -> None:
        """Several variables within one iif."""
        result = sub.substitute("{iif({%var.x} + {%var.y} > 10; 'big'; 'small')}", {"x": 7, "y": 5}, scope, ctx, state, params)
        assert "big" in result

    def test_iif_false_branch(self, sub, scope, ctx, state, params) -> None:
        """iif returns false if the condition is not met."""
        result = sub.substitute("{iif({%var.x} > 100; 'big'; 'small')}", {"x": 5}, scope, ctx, state, params)
        assert "small" in result


# ═════════════════════════════════════════════════════════════════════════════
#substitute() - full cycle of public API
# ═════════════════════════════════════════════════════════════════════════════

class TestSubstitutePublicAPI:
    """Full cycle through the only public method substitute()."""

    def test_plain_text_no_variables(self, sub, scope, ctx, state, params) -> None:
        """Text without variables is returned as is."""
        result = sub.substitute("Hello, world!", {}, scope, ctx, state, params)
        assert result == "Hello, world!"

    def test_single_variable(self, sub, scope, ctx, state, params) -> None:
        """One variable is substituted."""
        result = sub.substitute("Amount: {%var.amount}", {"amount": 99.9}, scope, ctx, state, params)
        assert "99.9" in result

    def test_multiple_variables(self, sub, scope, ctx, state, params) -> None:
        """Several variables from different namespaces."""
        st = BaseState(txn="TXN-1")
        sc = LogScope(machine="M", mode="test", action="Act", aspect="a", nest_level=0)
        result = sub.substitute(
            "var={%var.x} state={%state.txn} scope={%scope.action}",
            {"x": 42}, sc, ctx, st, params,
        )
        assert "42" in result
        assert "TXN-1" in result
        assert "Act" in result

    def test_variable_with_color_and_iif(self, sub, scope, ctx, state, params) -> None:
        """Color + iif + regular variable in one template."""
        template = "{%var.label|green} {iif({%var.x} > 0; 'pos'; 'neg')}"
        result = sub.substitute(template, {"label": "Status", "x": 1}, scope, ctx, state, params)
        assert "\033[32m" in result
        assert "Status" in result
        assert "pos" in result

    def test_empty_template(self, sub, scope, ctx, state, params) -> None:
        """Empty pattern → empty string."""
        result = sub.substitute("", {}, scope, ctx, state, params)
        assert result == ""


# ═════════════════════════════════════════════════════════════════════════════
#Error Handling - LogTemplateError
# ═════════════════════════════════════════════════════════════════════════════

class TestErrorHandling:
    """All scenarios leading to LogTemplateError."""

    def test_missing_variable_raises(self, sub, scope, ctx, state, params) -> None:
        """Non-existent variable → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="not found"):
            sub.substitute("{%var.missing}", {}, scope, ctx, state, params)

    def test_unknown_namespace_raises(self, sub, scope, ctx, state, params) -> None:
        """Unknown namespace -> LogTemplateError."""
        with pytest.raises(LogTemplateError, match="Unknown namespace"):
            sub.substitute("{%unknown.field}", {}, scope, ctx, state, params)

    def test_underscore_in_path_raises(self, sub, scope, ctx, state, params) -> None:
        """Underscore in any segment → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="underscore"):
            sub.substitute("{%context._internal.key}", {}, scope, ctx, state, params)

    def test_unknown_color_raises(self, sub, scope, ctx, state, params) -> None:
        """Unknown color in filter → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="color"):
            sub.substitute("{%var.x|rainbow}", {"x": "test"}, scope, ctx, state, params)

    def test_missing_variable_in_iif_raises(self, sub, scope, ctx, state, params) -> None:
        """Non-existent variable inside iif -> LogTemplateError."""
        with pytest.raises(LogTemplateError, match="not found"):
            sub.substitute("{iif({%var.missing} > 0; 'a'; 'b')}", {}, scope, ctx, state, params)

    def test_underscore_in_iif_raises(self, sub, scope, ctx, state, params) -> None:
        """Underscore inside iif → LogTemplateError."""
        with pytest.raises(LogTemplateError, match="underscore"):
            sub.substitute("{iif({%var._hidden}; 'a'; 'b')}", {"_hidden": True}, scope, ctx, state, params)
            sub.substitute("{iif({%var._hidden}; 'a'; 'b')}", {"_hidden": True}, scope, ctx, state, params)
