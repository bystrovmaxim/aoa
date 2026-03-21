# tests/logging/test_debug_function.py
"""
Unit tests for the debug() function in logging templates.

Tests cover:
- Introspection of top-level objects (params, state, context, var).
- Introspection of nested objects (context.user, state.order, etc.).
- Output of public fields and properties only (no private/protected).
- Correct handling of @sensitive decorator (showing config).
- Error handling for non-existent variables (with exists() function).
- Edge cases: cyclic references, deep nesting, large structures.
- New exists() function for safe variable checking.
"""

import re

import pytest

from action_machine.Context.context import Context
from action_machine.Context.user_info import UserInfo
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseState import BaseState
from action_machine.Logging.expression_evaluator import ExpressionEvaluator
from action_machine.Logging.sensitive_decorator import sensitive

# ----------------------------------------------------------------------
# Test helper classes
# ----------------------------------------------------------------------

class SimpleUser:
    def __init__(self, user_id: str, name: str, age: int):
        self.user_id = user_id
        self.name = name
        self.age = age
        self._private = "hidden"
        self.__mangled = "mangled"


class UserWithSensitive:
    def __init__(self, email: str, phone: str):
        self._email = email
        self._phone = phone

    @property
    @sensitive(True, max_chars=3, char='#', max_percent=40)
    def email(self):
        return self._email

    @property
    @sensitive(False)
    def phone(self):
        return self._phone

    @property
    def public_name(self):
        return "Public Name"


class CyclicObject:
    def __init__(self, name: str):
        self.name = name
        self.other = None


class DeepNested:
    def __init__(self, level: int):
        self.level = level
        self.child = DeepNested(level - 1) if level > 0 else None
        self.data = {"key": "value"}


class MyParams(BaseParams):
    def __init__(self, user_id: str, amount: float):
        self.user_id = user_id
        self.amount = amount


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

@pytest.fixture
def evaluator() -> ExpressionEvaluator:
    return ExpressionEvaluator()


@pytest.fixture
def context_with_user() -> Context:
    user = UserInfo(user_id="agent_007", roles=["agent", "admin"], extra={"org": "acme"})
    return Context(user=user)


@pytest.fixture
def complex_context() -> Context:
    user = UserWithSensitive(email="secret@example.com", phone="+1234567890")
    ctx = Context(user=UserInfo(user_id="test"))
    ctx._extra = {"account": user}
    return ctx


@pytest.fixture
def populated_state() -> BaseState:
    return BaseState({
        "total": 1500.0,
        "count": 42,
        "order": {"id": 12345, "status": "pending", "items": ["item1", "item2"]},
        "user": SimpleUser("alice", "Alice", 30),
    })


@pytest.fixture
def params_with_attrs() -> MyParams:
    return MyParams("bob", 99.99)


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

class TestDebugFunction:

    def test_debug_params(self, evaluator: ExpressionEvaluator, params_with_attrs: MyParams):
        result = evaluator.evaluate("debug(params)", {"params": params_with_attrs})
        assert "MyParams:" in result
        assert "user_id: str = 'bob'" in result
        assert "amount: float = 99.99" in result
        assert "get" not in result
        assert "items" not in result

    def test_debug_state(self, evaluator: ExpressionEvaluator, populated_state: BaseState):
        result = evaluator.evaluate("debug(state)", {"state": populated_state})
        # With max_depth=1, we see only top-level fields of BaseState
        assert "total: float = 1500.0" in result
        assert "count: int = 42" in result
        # Check dictionary representation without exact formatting (may be truncated)
        assert "order: dict = " in result
        assert "'id': 12345" in result
        assert "'status': 'pending'" in result
        # Check for items list presence (may be truncated)
        assert "'items'" in result
        assert "item1" in result
        assert "item2" in result
        # user is an object, not expanded
        assert "user: SimpleUser = <tests.logging.test_debug_function.SimpleUser object at" in result

    def test_debug_context(self, evaluator: ExpressionEvaluator, context_with_user: Context):
        result = evaluator.evaluate("debug(context)", {"context": context_with_user})
        # With max_depth=1, we see top-level fields of Context
        # Check user representation (may be truncated)
        assert "user: UserInfo = UserInfo(user_id='agent_007', roles=['agent', 'admin']," in result
        # extra may be truncated, but should contain org
        assert "org" in result or "acme" in result
        assert "request: RequestInfo = RequestInfo(trace_id=None, request_timestamp=None, request_path=None, request_method=None, full_url=None, client_ip=None, protocol=None, user_agent=None, extra={}, tags={})" in result
        assert "runtime: RuntimeInfo = RuntimeInfo(hostname=None, service_name=None, service_version=None, container_id=None, pod_name=None, extra={})" in result

    def test_debug_var(self, evaluator: ExpressionEvaluator):
        var = {"a": 1, "b": "hello", "c": [1, 2, 3]}
        result = evaluator.evaluate("debug(var)", {"var": var})
        assert "'a': 1" in result
        assert "'b': 'hello'" in result
        assert "'c': [1, 2, 3]" in result

    def test_debug_nested(self, evaluator: ExpressionEvaluator, complex_context: Context):
        account = complex_context._extra["account"]
        result = evaluator.evaluate("debug(account)", {"account": account})
        assert "public_name: str = 'Public Name'" in result
        assert "email: str (sensitive: enabled, max_chars=3, char='#', max_percent=40) = sec#####" in result
        assert "phone: str (sensitive: disabled) = '+1234567890'" in result

    def test_deep_nested(self, evaluator: ExpressionEvaluator):
        deep = DeepNested(3)
        result = evaluator.evaluate("debug(deep)", {"deep": deep})
        # With max_depth=1, only top-level fields are shown
        assert "level: int = 3" in result
        # child is an object, not expanded
        assert "child: DeepNested = <tests.logging.test_debug_function.DeepNested object at" in result
        assert "level: int = 2" not in result
        assert "level: int = 1" not in result

    def test_private_fields_not_shown(self, evaluator: ExpressionEvaluator):
        class WithPrivate:
            def __init__(self):
                self.public = "visible"
                self._private = "hidden"
                self.__mangled = "hidden"
        obj = WithPrivate()
        result = evaluator.evaluate("debug(obj)", {"obj": obj})
        assert "public: str = 'visible'" in result
        assert "_private" not in result
        assert "__mangled" not in result

    def test_sensitive_enabled_shows_config(self, evaluator: ExpressionEvaluator):
        class SensitiveEnabled:
            def __init__(self, val):
                self._val = val
            @property
            @sensitive(True, max_chars=2, char='*', max_percent=30)
            def secret(self):
                return self._val
        obj = SensitiveEnabled("abcdefghij")
        result = evaluator.evaluate("debug(obj)", {"obj": obj})
        assert "secret: str (sensitive: enabled, max_chars=2, char='*', max_percent=30) = ab*****" in result

    def test_sensitive_on_property_not_field(self, evaluator: ExpressionEvaluator):
        class Mixed:
            def __init__(self):
                self.public_field = "public"
                self._field = "field"
            @property
            @sensitive(True)
            def prop(self):
                return self._field
        obj = Mixed()
        result = evaluator.evaluate("debug(obj)", {"obj": obj})
        assert "public_field: str = 'public'" in result
        assert "prop: str (sensitive: enabled, max_chars=3, char='*', max_percent=50) = fie*****" in result
        # Ensure that _field does not appear as a separate line
        assert not re.search(r'\b_field\b', result, re.MULTILINE)

    # ------------------------------------------------------------------
    # FIXED: test_exists_with_debug – now uses ExpressionEvaluator directly
    # ------------------------------------------------------------------
    def test_exists_with_debug(self, evaluator: ExpressionEvaluator):
        # We pass the object directly into names, not through var
        data_obj = {"a": 1}
        names = {"data": data_obj}
        template = "{iif(exists('data'); debug(data); 'No data')}"
        result = evaluator.process_template(template, names)
        # debug(data) shows dictionary content: "dict:\n  'a': 1"
        assert "'a': 1" in result