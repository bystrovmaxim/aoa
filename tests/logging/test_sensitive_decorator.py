# tests/logging/test_sensitive_decorator.py
"""
Unit tests for the @sensitive decorator and masking functionality.
"""

import pytest

from action_machine.Context.context import Context
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseState import BaseState
from action_machine.Core.Exceptions import LogTemplateError
from action_machine.Logging.log_scope import LogScope
from action_machine.Logging.sensitive_decorator import sensitive
from action_machine.Logging.variable_substitutor import VariableSubstitutor


class TestSensitiveDecorator:
    """Tests for the @sensitive decorator and masking logic in VariableSubstitutor."""

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
    # Test classes with different field types
    # ------------------------------------------------------------------

    class PlainClass:
        """Class with a public field (no property)."""
        def __init__(self):
            self.public_field = "public value"

    class ClassWithProperty:
        """Class with a property that has no decorator."""
        def __init__(self):
            self._value = "secret"

        @property
        def value(self):
            return self._value

    class ClassWithSensitive:
        """Class with a property decorated with @sensitive (enabled)."""
        def __init__(self):
            self._email = "user@example.com"

        @property
        @sensitive(True, max_chars=3, char='#', max_percent=50)
        def email(self):
            return self._email

    class ClassWithDefaultSensitive:
        """Class with a property using default @sensitive parameters (enabled)."""
        def __init__(self):
            self._phone = "+1234567890"

        @property
        @sensitive(True)
        def phone(self):
            return self._phone

    class ClassWithDisabledSensitive:
        """Class with a property where sensitive is disabled."""
        def __init__(self):
            self._value = "secret"

        @property
        @sensitive(False, max_chars=2)
        def value(self):
            return self._value

    class ClassWithNumericSensitive:
        def __init__(self):
            self._code = 12345

        @property
        @sensitive(True, max_chars=2)
        def code(self):
            return self._code

    class ClassWithBoolSensitive:
        def __init__(self):
            self._flag = True

        @property
        @sensitive(True, max_chars=1)
        def flag(self):
            return self._flag

    class ClassWithPrivate:
        """Class with a private field (underscored)."""
        def __init__(self):
            self._secret = "private data"

    class ClassWithUnderscoreProperty:
        """Class with a property whose name starts with underscore."""
        def __init__(self):
            self._x_val = 42

        @property
        def _x(self):
            return self._x_val

    class ClassWithLongString:
        def __init__(self):
            self._long = "abcdefghijklmnopqrstuvwxyz"

        @property
        @sensitive(True, max_chars=10, max_percent=20)
        def long(self):
            return self._long

    # ------------------------------------------------------------------
    # Tests for public field (no property)
    # ------------------------------------------------------------------

    def test_public_field_no_masking(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """A plain public field is output as is (no masking)."""
        obj = self.PlainClass()
        result = substitutor.substitute(
            "{%var.obj.public_field}",
            {"obj": obj},
            empty_scope,
            empty_context,
            empty_state,
            empty_params
        )
        assert result == "public value"

    # ------------------------------------------------------------------
    # Tests for property without decorator
    # ------------------------------------------------------------------

    def test_property_no_decorator(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """A property without @sensitive outputs the raw value."""
        obj = self.ClassWithProperty()
        result = substitutor.substitute(
            "{%var.obj.value}",
            {"obj": obj},
            empty_scope,
            empty_context,
            empty_state,
            empty_params
        )
        assert result == "secret"

    # ------------------------------------------------------------------
    # Tests for property with @sensitive (custom parameters)
    # ------------------------------------------------------------------

    def test_sensitive_property_masking(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """A property with @sensitive should be masked."""
        obj = self.ClassWithSensitive()
        result = substitutor.substitute(
            "{%var.obj.email}",
            {"obj": obj},
            empty_scope,
            empty_context,
            empty_state,
            empty_params
        )
        # email = "user@example.com" – show max_chars=3, so "use" + 5 '#'
        assert result == "use#####"

    def test_sensitive_property_default_params(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """A property with default @sensitive (max_chars=3, char='*', max_percent=50)."""
        obj = self.ClassWithDefaultSensitive()
        # phone = "+1234567890" (11 chars). max_percent=50 → 5.5 → ceil 6, but max_chars=3, so keep 3.
        result = substitutor.substitute(
            "{%var.obj.phone}",
            {"obj": obj},
            empty_scope,
            empty_context,
            empty_state,
            empty_params
        )
        assert result == "+12*****"  # first 3 chars + 5 '*'

    # ------------------------------------------------------------------
    # Tests for disabled @sensitive
    # ------------------------------------------------------------------

    def test_sensitive_disabled(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """When enabled=False, no masking should occur."""
        obj = self.ClassWithDisabledSensitive()
        result = substitutor.substitute(
            "{%var.obj.value}",
            {"obj": obj},
            empty_scope,
            empty_context,
            empty_state,
            empty_params
        )
        assert result == "secret"  # no masking

    # ------------------------------------------------------------------
    # Tests for numeric and boolean values with @sensitive
    # ------------------------------------------------------------------

    def test_numeric_sensitive(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Numeric values are converted to string and masked."""
        obj = self.ClassWithNumericSensitive()
        result = substitutor.substitute(
            "{%var.obj.code}",
            {"obj": obj},
            empty_scope,
            empty_context,
            empty_state,
            empty_params
        )
        # "12345" → first 2 chars "12" + 5 '*'
        assert result == "12*****"

    def test_bool_sensitive(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Boolean values are converted to string and masked."""
        obj = self.ClassWithBoolSensitive()
        result = substitutor.substitute(
            "{%var.obj.flag}",
            {"obj": obj},
            empty_scope,
            empty_context,
            empty_state,
            empty_params
        )
        # "True" → first 1 char "T" + 5 '*'
        assert result == "T*****"

    # ------------------------------------------------------------------
    # Tests for underscore rule (should raise exception)
    # ------------------------------------------------------------------

    def test_underscore_field_raises(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """Accessing a field with underscore in the last segment raises LogTemplateError."""
        obj = self.ClassWithPrivate()
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            substitutor.substitute(
                "{%var.obj._secret}",
                {"obj": obj},
                empty_scope,
                empty_context,
                empty_state,
                empty_params
            )

    def test_underscore_property_raises(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """
        Even if it's a property, if the name starts with underscore, it's forbidden.
        """
        obj = self.ClassWithUnderscoreProperty()
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            substitutor.substitute(
                "{%var.obj._x}",
                {"obj": obj},
                empty_scope,
                empty_context,
                empty_state,
                empty_params
            )

    # ------------------------------------------------------------------
    # Tests for masking with different max_percent
    # ------------------------------------------------------------------

    def test_max_percent_limit(self, substitutor, empty_context, empty_scope, empty_state, empty_params):
        """max_percent should limit shown characters even if max_chars is larger."""
        obj = self.ClassWithLongString()
        # string length 26, max_percent=20 → 5.2 → ceil 6, max_chars=10, so show 6 chars.
        result = substitutor.substitute(
            "{%var.obj.long}",
            {"obj": obj},
            empty_scope,
            empty_context,
            empty_state,
            empty_params
        )
        assert result == "abcdef*****"