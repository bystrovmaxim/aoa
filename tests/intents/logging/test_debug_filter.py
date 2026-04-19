# tests/intents/logging/test_debug_filter.py
"""|debug filter tests in logging templates.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

The |debug filter outputs a formatted introspection of an object: its public fields,
@sensitive types, values and configuration. Used for debugging in logs:
{%var.obj|debug}, {%state|debug}, {%context.user|debug}.

The |debug filter is shorthand for the debug() function, which is defined
in ExpressionEvaluator and calls _inspect_object with max_depth=1 (only
immediate fields). Nested objects are not expanded to prevent
clog the logs.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

- Basic usage: {%var.obj|debug} outputs an introspection of an object.
- The output contains public fields and properties, types and values.
- Masking of sensitive data (@sensitive) is preserved.
- Nested objects are NOT expanded (max_depth=1).
- Works inside and outside iif blocks.
- Works with all namespaces (var, state, context, params, scope).
- Handling None, empty collections.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
CYCLE DETECTION
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Circular links are detected through a set of visited (id objects).
With max_depth=1 (default value for debug()) loop A→B→A
is only detected at the self-reference level (A.self_ref = A) because
B is not expanded recursively and its fields are not checked. For detection
loops through intermediate objects (A→B→A) you need max_depth >= 2.

The test_debug_on_self_reference test checks for direct self-reference (max_depth=1).
The test_debug_on_indirect_cycle tests the indirect cycle (max_depth=2)
via _inspect_object directly."""

import pytest

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.intents.logging.expression_evaluator import ExpressionEvaluator, _inspect_object
from action_machine.intents.logging.log_scope import LogScope
from action_machine.intents.logging.sensitive_decorator import sensitive
from action_machine.intents.logging.variable_substitutor import VariableSubstitutor
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState
from tests.scenarios.domain_model.roles import UserRole

# ======================================================================
#Helper classes
# ======================================================================

class SimpleObj:
    """A simple object with public and private fields."""
    def __init__(self):
        self.name = "Simple"
        self.value = 42
        self._private = "hidden"


class UserWithSensitive:
    """Class with sensitive property."""
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
    """An object with a nested structure to check for the absence of recursion."""
    def __init__(self):
        self.level1 = "visible"
        self.child = self.Child()

    class Child:
        def __init__(self):
            self.level2 = "hidden"


class SelfRefObj:
    """An object with a direct self-reference is a loop of length 1."""
    def __init__(self, name: str):
        self.name = name
        self.self_ref = self


class CyclicObj:
    """Object for constructing an indirect cycle A→B→A."""
    def __init__(self, name: str):
        self.name = name
        self.other = None


# ======================================================================
#Fittings
# ======================================================================

@pytest.fixture
def substitutor() -> VariableSubstitutor:
    return VariableSubstitutor()


@pytest.fixture
def evaluator() -> ExpressionEvaluator:
    return ExpressionEvaluator()


@pytest.fixture
def empty_scope() -> LogScope:
    return LogScope()


@pytest.fixture
def empty_context() -> Context:
    return Context()


@pytest.fixture
def empty_state() -> BaseState:
    return BaseState()


@pytest.fixture
def empty_params() -> BaseParams:
    return BaseParams()


# ======================================================================
#TESTS: Basic usage |debug
# ======================================================================

class TestDebugFilterBasic:
    """The |debug filter outputs an introspection of an object."""

    def test_debug_on_simple_object(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{%var.obj|debug} displays SimpleObj's public fields."""
        #Arrange is a simple object with public and private fields
        obj = SimpleObj()
        var = {"obj": obj}

        #Act - template substitution with |debug filter
        result = substitutor.substitute(
            "{%var.obj|debug}",
            var, empty_scope, empty_context, empty_state, empty_params,
        )

        #Assert - public fields are visible, private fields are hidden
        assert "SimpleObj:" in result
        assert "name: str = 'Simple'" in result
        assert "value: int = 42" in result
        assert "_private" not in result

    def test_debug_on_dict(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{%var.data|debug} on the dictionary displays the contents."""
        #Arrange - dictionary with nested data
        data = {"a": 1, "b": 2, "c": {"nested": "value"}}

        # Act
        result = substitutor.substitute(
            "{%var.data|debug}",
            {"data": data}, empty_scope, empty_context, empty_state, empty_params,
        )

        #Assert - keys and values ​​are visible
        assert "dict:" in result
        assert "'a': 1" in result
        assert "'b': 2" in result
        assert "'c': {'nested': 'value'}" in result

    def test_debug_on_sensitive_property(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """The |debug filter respects the @sensitive decorator."""
        #Arrange - an object with sensitive and disabled @sensitive properties
        user = UserWithSensitive("secret@example.com", "+1234567890")

        # Act
        result = substitutor.substitute(
            "{%var.user|debug}",
            {"user": user}, empty_scope, empty_context, empty_state, empty_params,
        )

        #Assert - email is masked, phone is shown as is (sensitive: disabled)
        assert "email: str (sensitive: enabled, max_chars=3, char='#', max_percent=50) = sec#####" in result
        assert "phone: str (sensitive: disabled) = '+1234567890'" in result
        assert "public_name: str = 'Public Name'" in result

    def test_debug_no_recursion(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """The |debug filter does not expand nested objects (max_depth=1).
        The nested Child is shown as repr(value) - a string with the address of the object.
        The fields of the nested object (level2) are not visible."""
        #Arrange - an object with a nested structure
        obj = DeepObj()

        # Act
        result = substitutor.substitute(
            "{%var.obj|debug}",
            {"obj": obj}, empty_scope, empty_context, empty_state, empty_params,
        )

        #Assert - the first level is visible, the nested object is not expanded
        assert "DeepObj:" in result
        assert "level1: str = 'visible'" in result
        #The attached object is shown as repr - contains the name of the class.
        #We check only the class name, without the full path of the module,
        #because the path depends on the location of the tests (tests/ vs tests/).
        assert "child: Child" in result
        assert "level2" not in result


# ======================================================================
#TESTS: |debug with different namespaces
# ======================================================================

class TestDebugNamespaces:
    """The |debug filter works with all namespaces."""

    def test_debug_on_context(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{%context.user|debug} - introspection of UserInfo from the context."""
        #Arrange - context with user and extra data
        user = UserInfo(user_id="test_user", roles=(UserRole,))
        ctx = Context(user=user)

        # Act
        result = substitutor.substitute(
            "{%context.user|debug}",
            {}, empty_scope, ctx, empty_state, empty_params,
        )

        #Assert - UserInfo fields are visible
        assert "UserInfo:" in result
        assert "UserInfo:" in result
        assert "user_id: str = 'test_user'" in result
        assert "roles: tuple" in result
        assert "UserRole" in result

    def test_debug_on_state(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context, empty_params: BaseParams,
    ) -> None:
        """{%state|debug} - BaseState introspection."""
        #Arrange - state with number and list
        state = BaseState(total=100, items=[1, 2, 3])

        # Act
        result = substitutor.substitute(
            "{%state|debug}",
            {}, empty_scope, empty_context, state, empty_params,
        )

        #Assert - status fields are visible
        assert "total: int = 100" in result
        assert "items: list = [1, 2, 3]" in result

    def test_debug_on_params(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context, empty_state: BaseState,
    ) -> None:
        """{%params|debug} - introspection of the pydantic model."""
        #Arrange - pydantic model with margins
        class MyParams(BaseParams):
            param1: str
            param2: int

        params = MyParams(param1="hello", param2=42)

        # Act
        result = substitutor.substitute(
            "{%params|debug}",
            {}, empty_scope, empty_context, empty_state, params,
        )

        #Assert—pydantic model fields are visible
        assert "MyParams:" in result
        assert "param1: str = 'hello'" in result
        assert "param2: int = 42" in result

    def test_debug_on_scope(
        self, substitutor: VariableSubstitutor,
        empty_context: Context, empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{%scope|debug} - LogScope introspection."""
        #Arrange - scope with multiple fields
        scope = LogScope(machine="TestMachine", mode="test", action="TestAction", aspect="test")

        # Act
        result = substitutor.substitute(
            "{%scope|debug}",
            {}, scope, empty_context, empty_state, empty_params,
        )

        #Assert - scope fields are visible
        assert "machine: str = 'TestMachine'" in result
        assert "mode: str = 'test'" in result
        assert "action: str = 'TestAction'" in result
        assert "aspect: str = 'test'" in result


# ======================================================================
#TESTS: |debug inside iif
# ======================================================================

class TestDebugInsideIif:
    """The |debug filter works inside iif."""

    def test_debug_filter_inside_iif(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{iif(1==1; {%var.obj|debug}; '')} — debug is running."""
        # Arrange
        obj = SimpleObj()
        template = "{iif(1==1; {%var.obj|debug}; '')}"

        # Act
        result = substitutor.substitute(
            template, {"obj": obj}, empty_scope, empty_context, empty_state, empty_params,
        )

        #Assert — debug output is present
        assert "SimpleObj:" in result
        assert "name: str = 'Simple'" in result

    def test_debug_with_exists(
        self, evaluator: ExpressionEvaluator,
    ) -> None:
        """exists() and debug() in iif are safe introspection."""
        #Arrange - the object is in the context
        obj = SimpleObj()
        template = "{iif(exists('obj'); debug(obj); 'No object')}"

        #Act - there is an object
        result = evaluator.process_template(template, {"obj": obj})

        # Assert
        assert "SimpleObj:" in result

        #Act - no object
        result2 = evaluator.process_template(template, {})

        # Assert
        assert result2 == "No object"


# ======================================================================
#TESTS: Boundary Cases
# ======================================================================

class TestDebugEdgeCases:
    """Handling None, empty objects, loops."""

    def test_debug_on_none(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """{%var.nothing|debug} to None outputs 'NoneType = None'."""
        # Arrange & Act
        result = substitutor.substitute(
            "{%var.nothing|debug}",
            {"nothing": None}, empty_scope, empty_context, empty_state, empty_params,
        )

        # Assert
        assert "NoneType = None" in result

    def test_debug_on_empty_list(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """An empty list outputs 'list[]'."""
        # Arrange & Act
        result = substitutor.substitute(
            "{%var.empty|debug}",
            {"empty": []}, empty_scope, empty_context, empty_state, empty_params,
        )

        # Assert
        assert "list[]" in result

    def test_debug_on_empty_dict(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """An empty dictionary outputs 'dict{}'."""
        # Arrange & Act
        result = substitutor.substitute(
            "{%var.empty|debug}",
            {"empty": {}}, empty_scope, empty_context, empty_state, empty_params,
        )

        # Assert
        assert "dict{}" in result

    def test_debug_on_self_reference(
        self, substitutor: VariableSubstitutor,
        empty_scope: LogScope, empty_context: Context,
        empty_state: BaseState, empty_params: BaseParams,
    ) -> None:
        """A direct self-ref (obj.self_ref = obj) is detected when max_depth=1.

        The object adds its id to visited when entering _inspect_object.
        When _format_field_line processes the self_ref field, id(self_ref)
        matches id(obj) (they are the same object) and the field is marked
        <cycle detected>."""
        #Arrange - an object refers to itself
        obj = SelfRefObj("A")

        # Act
        result = substitutor.substitute(
            "{%var.obj|debug}",
            {"obj": obj}, empty_scope, empty_context, empty_state, empty_params,
        )

        #Assert - self-link detected
        assert "SelfRefObj:" in result
        assert "name: str = 'A'" in result
        assert "<cycle detected>" in result

    def test_debug_on_indirect_cycle(self) -> None:
        """The indirect cycle A→B→A is detected at max_depth=2.

        With max_depth=1 (debug by default) object B is shown as
        repr(value), and its fields are not checked - the loop is not visible.
        With max_depth=2 _inspect_object goes inside B, detects
        B.other=A, and id(A) is already in visited → <cycle detected>."""
        #Arrange - two objects referencing each other
        a = CyclicObj("A")
        b = CyclicObj("B")
        a.other = b
        b.other = a

        #Act - max_depth=2 for indirect loop detection
        result = _inspect_object(a, max_depth=2)

        #Assert - cycle detected at the second level
        assert "CyclicObj:" in result
        assert "name: str = 'A'" in result
        assert "<cycle detected>" in result
        assert "<cycle detected>" in result
