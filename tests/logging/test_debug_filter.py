# tests/logging/test_debug_filter.py
"""
Unit tests for the |debug filter in logging templates.

Tests cover:
- Basic usage: {%var.obj|debug} outputs object introspection.
- Output includes public fields and properties, types, and values.
- Sensitive data masking is preserved when the property has @sensitive.
- Nested objects are NOT expanded (max_depth=1).
- Works both inside and outside iif blocks.
- Works with all namespaces (var, state, context, params, scope).
"""

import pytest

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.expression_evaluator import ExpressionEvaluator
from action_machine.logging.log_scope import LogScope
from action_machine.logging.sensitive_decorator import sensitive
from action_machine.logging.variable_substitutor import VariableSubstitutor

# ----------------------------------------------------------------------
# Helper classes
# ----------------------------------------------------------------------

class SimpleObj:
    """A simple object with public fields and a private field."""
    def __init__(self):
        self.name = "Simple"
        self.value = 42
        self._private = "hidden"


class UserWithSensitive:
    """Class with a sensitive property."""
    def __init__(self, email: str, phone: str):
        self._email = email
        self._phone = phone

    @property
    @sensitive(True, max_chars=3, char='#', max_percent=50)
    def email(self):
        return self._email

    @property
    @sensitive(False)
    def phone(self):
        return self._phone

    @property
    def public_name(self):
        return "Public Name"


class DeepObj:
    """Object with nested structure to verify non-recursion."""
    def __init__(self):
        self.level1 = "visible"
        self.child = self.Child()

    class Child:
        def __init__(self):
            self.level2 = "hidden"


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

@pytest.fixture
def substitutor():
    return VariableSubstitutor()


@pytest.fixture
def empty_scope():
    return LogScope()


@pytest.fixture
def empty_context():
    return Context()


@pytest.fixture
def empty_state():
    return BaseState()


@pytest.fixture
def empty_params():
    return BaseParams()


@pytest.fixture
def evaluator():
    """ExpressionEvaluator for tests that need direct iif evaluation."""
    return ExpressionEvaluator()


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

class TestDebugFilter:
    """Tests for the |debug filter."""

    def test_debug_filter_on_simple_object(self, substitutor, empty_scope, empty_context, empty_state, empty_params):
        """Basic test: debug filter outputs public fields."""
        obj = SimpleObj()
        var = {"obj": obj}
        template = "{%var.obj|debug}"
        result = substitutor.substitute(
            template, var=var, scope=empty_scope, ctx=empty_context,
            state=empty_state, params=empty_params
        )
        # Check presence of expected fields
        assert "SimpleObj:" in result
        assert "name: str = 'Simple'" in result
        assert "value: int = 42" in result
        # Private field should NOT appear
        assert "_private" not in result

    def test_debug_filter_on_dict(self, substitutor, empty_scope, empty_context, empty_state, empty_params):
        """Debug filter on a dictionary."""
        data = {"a": 1, "b": 2, "c": {"nested": "value"}}
        var = {"data": data}
        template = "{%var.data|debug}"
        result = substitutor.substitute(
            template, var=var, scope=empty_scope, ctx=empty_context,
            state=empty_state, params=empty_params
        )
        # Dictionary output is flat (no recursion)
        assert "dict:" in result
        assert "'a': 1" in result
        assert "'b': 2" in result
        assert "'c': {'nested': 'value'}" in result

    def test_debug_filter_on_sensitive_property(self, substitutor, empty_scope, empty_context, empty_state, empty_params):
        """Debug filter respects @sensitive decorator."""
        user = UserWithSensitive("secret@example.com", "+1234567890")
        var = {"user": user}
        template = "{%var.user|debug}"
        result = substitutor.substitute(
            template, var=var, scope=empty_scope, ctx=empty_context,
            state=empty_state, params=empty_params
        )
        # Email should be masked
        assert "email: str (sensitive: enabled, max_chars=3, char='#', max_percent=50) = sec#####" in result
        # Phone should be visible (masking disabled)
        assert "phone: str (sensitive: disabled) = '+1234567890'" in result
        # Public property should be visible
        assert "public_name: str = 'Public Name'" in result

    def test_debug_filter_no_recursion(self, substitutor, empty_scope, empty_context, empty_state, empty_params):
        """Debug filter should not expand nested objects (max_depth=1)."""
        obj = DeepObj()
        var = {"obj": obj}
        template = "{%var.obj|debug}"
        result = substitutor.substitute(
            template, var=var, scope=empty_scope, ctx=empty_context,
            state=empty_state, params=empty_params
        )
        assert "DeepObj:" in result
        assert "level1: str = 'visible'" in result
        # child is an object, should be shown as type + object reference, not expanded
        assert "child: Child = <tests.logging.test_debug_filter.DeepObj.Child object at" in result
        # level2 should NOT appear in output (not expanded)
        assert "level2" not in result

    def test_debug_filter_inside_iif(self, substitutor, empty_scope, empty_context, empty_state, empty_params):
        """Debug filter can be used inside iif expressions."""
        obj = SimpleObj()
        var = {"obj": obj}
        template = "{iif(1==1; {%var.obj|debug}; '')}"
        result = substitutor.substitute(
            template, var=var, scope=empty_scope, ctx=empty_context,
            state=empty_state, params=empty_params
        )
        assert "SimpleObj:" in result
        assert "name: str = 'Simple'" in result

    def test_debug_filter_with_exists(self, evaluator):
        """Combined usage of exists and debug filter (using function inside iif)."""
        obj = SimpleObj()
        # Pass the object directly to the evaluator's names dict
        names = {"obj": obj}
        template = "{iif(exists('obj'); debug(obj); 'No object')}"
        result = evaluator.process_template(template, names)
        assert "SimpleObj:" in result
        # When object missing, fallback should be used
        result2 = evaluator.process_template(template, {})
        assert result2 == "No object"

    def test_debug_filter_on_context_object(self, substitutor, empty_scope, empty_state, empty_params):
        """Debug filter works with context namespace."""
        user = UserInfo(user_id="test_user", roles=["user"], extra={"org": "acme"})
        ctx = Context(user=user)
        template = "{%context.user|debug}"
        result = substitutor.substitute(
            template, var={}, scope=empty_scope, ctx=ctx,
            state=empty_state, params=empty_params
        )
        assert "UserInfo:" in result
        assert "user_id: str = 'test_user'" in result
        assert "roles: list = ['user']" in result
        assert "extra: dict = {'org': 'acme'}" in result

    def test_debug_filter_on_state(self, substitutor, empty_scope, empty_context, empty_params):
        """Debug filter works with state namespace (no __dict__ needed)."""
        state = BaseState({"total": 100, "items": [1, 2, 3]})
        template = "{%state|debug}"
        result = substitutor.substitute(
            template, var={}, scope=empty_scope, ctx=empty_context,
            state=state, params=empty_params
        )
        # BaseState outputs its public fields (the ones we set)
        assert "total: int = 100" in result
        assert "items: list = [1, 2, 3]" in result

    def test_debug_filter_on_params(self, substitutor, empty_scope, empty_context, empty_state):
        """Debug filter works with params namespace."""
        class MyParams(BaseParams):
            def __init__(self):
                self.param1 = "hello"
                self.param2 = 42

        params = MyParams()
        template = "{%params|debug}"
        result = substitutor.substitute(
            template, var={}, scope=empty_scope, ctx=empty_context,
            state=empty_state, params=params
        )
        assert "MyParams:" in result
        assert "param1: str = 'hello'" in result
        assert "param2: int = 42" in result

    def test_debug_filter_on_scope(self, substitutor, empty_context, empty_state, empty_params):
        """Debug filter works with scope namespace."""
        scope = LogScope(machine="TestMachine", mode="test", action="TestAction", aspect="test")
        template = "{%scope|debug}"
        result = substitutor.substitute(
            template, var={}, scope=scope, ctx=empty_context,
            state=empty_state, params=empty_params
        )
        # LogScope inherits ReadableMixin; its public attributes are those passed to __init__
        assert "machine: str = 'TestMachine'" in result
        assert "mode: str = 'test'" in result
        assert "action: str = 'TestAction'" in result
        assert "aspect: str = 'test'" in result

    def test_debug_filter_on_missing_object_raises(self, substitutor, empty_scope, empty_context, empty_state, empty_params):
        """Accessing a non-existent variable with |debug should raise LogTemplateError."""
        var = {"obj": "some"}
        template = "{%var.missing|debug}"
        with pytest.raises(Exception) as exc_info:
            substitutor.substitute(
                template, var=var, scope=empty_scope, ctx=empty_context,
                state=empty_state, params=empty_params
            )
        assert "not found" in str(exc_info.value) or "LogTemplateError" in str(exc_info.value)

    def test_debug_filter_on_none_value(self, substitutor, empty_scope, empty_context, empty_state, empty_params):
        """Debug filter on None should output 'NoneType = None'."""
        var = {"nothing": None}
        template = "{%var.nothing|debug}"
        result = substitutor.substitute(
            template, var=var, scope=empty_scope, ctx=empty_context,
            state=empty_state, params=empty_params
        )
        assert "NoneType = None" in result
