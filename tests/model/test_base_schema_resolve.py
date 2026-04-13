# tests/model/test_base_schema_resolve.py
"""BaseSchema.resolve() tests for dot-path navigation on nested objects.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

BaseSchema.resolve("user.extra.org") traverses the chain of nested objects,
performing one navigation step on each path segment. Every step of the way
a navigation strategy is selected depending on the type of the current object:

1. BaseSchema → __getitem__ (dict-like access via pydantic fields).
2. dict → direct access by key.
3. Any other object → getattr.

A chain can contain objects of different types: Context (BaseSchema) →
UserInfo(BaseSchema) -> value.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Two levels of nesting:
    - Context → UserInfo → user_id (BaseSchema → BaseSchema → value).
    - Context → RequestInfo → trace_id (BaseSchema → BaseSchema → value).

Three or more levels:
    - Deep chain of BaseSchema objects (3+ levels).
    - BaseSchema → BaseSchema → BaseSchema → value.

Mixed types in a chain:
    - BaseSchema → dict → dict → value (via BaseState extra fields).
    - BaseSchema → BaseSchema → dict → value.

Navigation through dictionaries (via BaseState extra="allow"):
    - Easy access to value in extra-dict.
    - Nested dictionaries (dict → dict → dict).
    - Getting the whole dict as a value.
    - Getting a list from a dictionary.

Default if there is no intermediate key:
    - Intermediate BaseSchema does not contain fields → default.
    - The intermediate dict does not contain the key → default."""

from pydantic import ConfigDict

from action_machine.intents.context.context import Context
from action_machine.intents.context.request_info import RequestInfo
from action_machine.intents.context.runtime_info import RuntimeInfo
from action_machine.intents.context.user_info import UserInfo
from action_machine.model.base_schema import BaseSchema
from action_machine.model.base_state import BaseState
from tests.scenarios.domain_model.roles import AdminRole, AgentRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
#Helper classes
# ═════════════════════════════════════════════════════════════════════════════


class NestedSchema(BaseSchema):
    """An auxiliary scheme for creating arbitrary nested chains
    BaseSchema objects. Used for testing deep navigation.
    extra="allow" allows you to pass custom fields via kwargs."""

    model_config = ConfigDict(frozen=True, extra="allow")


# ═════════════════════════════════════════════════════════════════════════════
#Two levels of nesting
# ═════════════════════════════════════════════════════════════════════════════


class TestTwoLevels:
    """resolve through two levels: object → nested object → value."""

    def test_context_to_user_field(self) -> None:
        """resolve("user.user_id") - Context → UserInfo → user_id.

        First step: Context.__getitem__("user") → UserInfo.
        Second step: UserInfo.__getitem__("user_id") → "agent_007".
        Both objects are BaseSchema, the strategy is __getitem__."""
        # Arrange
        user = UserInfo(user_id="agent_007", roles=(AgentRole,))
        ctx = Context(user=user)

        # Act
        result = ctx.resolve("user.user_id")

        # Assert
        assert result == "agent_007"

    def test_context_to_user_roles(self) -> None:
        """resolve("user.roles") - access to a tuple of role types through nesting."""
        # Arrange
        user = UserInfo(user_id="42", roles=(AdminRole, UserRole))
        ctx = Context(user=user)

        # Act
        result = ctx.resolve("user.roles")

        # Assert
        assert result == (AdminRole, UserRole)

    def test_context_to_request_field(self) -> None:
        """
        resolve("request.trace_id") — Context → RequestInfo → trace_id.
        """
        # Arrange
        request = RequestInfo(trace_id="trace-abc-123", request_path="/api/v1/orders")
        ctx = Context(request=request)

        # Act
        result = ctx.resolve("request.trace_id")

        # Assert
        assert result == "trace-abc-123"

    def test_context_to_runtime_field(self) -> None:
        """
        resolve("runtime.hostname") — Context → RuntimeInfo → hostname.
        """
        # Arrange
        runtime = RuntimeInfo(hostname="pod-xyz-42", service_name="order-service")
        ctx = Context(runtime=runtime)

        # Act
        result = ctx.resolve("runtime.hostname")

        # Assert
        assert result == "pod-xyz-42"


# ═════════════════════════════════════════════════════════════════════════════
#Three or more levels of nesting
# ═════════════════════════════════════════════════════════════════════════════


class TestThreeOrMoreLevels:
    """resolve through three or more nesting levels."""

    def test_deep_schema_chain(self) -> None:
        """resolve("level1.level2.level3.value") - a chain of three
        nested BaseSchema objects to the final value."""
        #Arrange - three levels of nested NestedSchema
        level3 = NestedSchema(value="deep")
        level2 = NestedSchema(level3=level3)
        level1 = NestedSchema(level2=level2)
        root = NestedSchema(level1=level1)

        # Act
        result = root.resolve("level1.level2.level3.value")

        # Assert
        assert result == "deep"

    def test_deep_dict_nesting_via_state(self) -> None:
        """resolve("level1.level2.value") — BaseState → dict → dict → value.

        BaseState with extra="allow" stores arbitrary values,
        including nested dictionaries."""
        #Arrange - BaseState with deeply nested dictionaries
        state = BaseState(level1={"level2": {"value": "deep"}})

        # Act
        result = state.resolve("level1.level2.value")

        # Assert
        assert result == "deep"

    def test_four_level_dict_chain(self) -> None:
        """resolve("a.b.c.d") - four levels through dicts in BaseState."""
        # Arrange
        state = BaseState(a={"b": {"c": {"d": "found"}}})

        # Act
        result = state.resolve("a.b.c.d")

        # Assert
        assert result == "found"


# ═════════════════════════════════════════════════════════════════════════════
#Navigation through dictionaries
# ═════════════════════════════════════════════════════════════════════════════


class TestDictNavigation:
    """resolve via dictionaries (dicts) inside BaseSchema objects."""

    def test_state_dict_simple_key(self) -> None:
        """resolve("data.key") - BaseState → dict → value."""
        # Arrange
        state = BaseState(data={"key": "value"})

        # Act
        result = state.resolve("data.key")

        # Assert
        assert result == "value"

    def test_state_dict_nested_dicts(self) -> None:
        """resolve("data.nested.key") - dict → dict → value."""
        # Arrange
        state = BaseState(data={"nested": {"key": "value"}})

        # Act
        result = state.resolve("data.nested.key")

        # Assert
        assert result == "value"

    def test_state_dict_multiple_keys(self) -> None:
        """Several independent keys in one dictionary - each
        available via separate resolve."""
        # Arrange
        state = BaseState(data={"a": 1, "b": 2, "c": 3})

        # Act & Assert
        assert state.resolve("data.a") == 1
        assert state.resolve("data.b") == 2
        assert state.resolve("data.c") == 3

    def test_state_dict_returns_list(self) -> None:
        """resolve returns the list from the dictionary as a single value."""
        # Arrange
        state = BaseState(data={"items": [1, 2, 3, 4]})

        # Act
        result = state.resolve("data.items")

        # Assert
        assert result == [1, 2, 3, 4]
        assert isinstance(result, list)

    def test_state_dict_returns_whole_dict(self) -> None:
        """resolve returns the entire nested dictionary if path
        ends with a key whose value is dict."""
        # Arrange
        state = BaseState(data={"config": {"theme": "dark", "lang": "ru"}})

        # Act
        result = state.resolve("data.config")

        # Assert
        assert result == {"theme": "dark", "lang": "ru"}
        assert isinstance(result, dict)

    def test_state_dict_with_none_value(self) -> None:
        """The None value in the dictionary is a valid value, not an absence.
        resolve returns None, not default."""
        # Arrange
        state = BaseState(data={"key": None})

        # Act
        result = state.resolve("data.key")

        #Assert — None from the dictionary, not default
        assert result is None

    def test_state_empty_dict_returns_default(self) -> None:
        """resolve on an empty dictionary using a non-existent key → default."""
        # Arrange
        state = BaseState(data={})

        # Act
        result = state.resolve("data.key", default="empty")

        # Assert
        assert result == "empty"


# ═════════════════════════════════════════════════════════════════════════════
#Mixed types in a chain
# ═════════════════════════════════════════════════════════════════════════════


class TestMixedTypes:
    """resolve through mixed types: BaseSchema, dict, regular objects."""

    def test_schema_then_dict_then_dict(self) -> None:
        """BaseState → dict (settings) → dict (notifications) → value.

        The navigation strategy changes: BaseSchema → dict → dict → value."""
        # Arrange
        state = BaseState(
            settings={"theme": "dark", "notifications": {"email": True}},
        )

        # Act & Assert
        assert state.resolve("settings.theme") == "dark"
        assert state.resolve("settings.notifications.email") is True

    def test_context_schema_schema_value(self) -> None:
        """Context → UserInfo → user_id is a pure BaseSchema chain."""
        # Arrange
        ctx = Context(
            user=UserInfo(user_id="42"),
            request=RequestInfo(trace_id="abc"),
        )

        # Act & Assert
        assert ctx.resolve("user.user_id") == "42"
        assert ctx.resolve("request.trace_id") == "abc"

    def test_default_on_missing_intermediate_field(self) -> None:
        """If the intermediate field is not found, resolve returns default,
        without throwing an exception. __getitem__ throws KeyError, resolve
        catches it and returns default."""
        # Arrange
        ctx = Context(user=UserInfo(user_id="42"))

        #Act - "nonexistent" is not among the UserInfo fields
        result = ctx.resolve("user.nonexistent.deep", default="N/A")

        # Assert
        assert result == "N/A"

    def test_default_on_missing_dict_key(self) -> None:
        """Intermediate key not found in dictionary → default."""
        # Arrange
        state = BaseState(data={"existing": "value"})

        #Act - key "missing" does not exist in dict
        result = state.resolve("data.missing.deep", default="not found")

        # Assert
        assert result == "not found"

    def test_default_on_completely_missing_path(self) -> None:
        """The first segment of the path was not found → default."""
        # Arrange
        state = BaseState(total=100)

        # Act
        result = state.resolve("nonexistent.deep.path", default="gone")

        # Assert
        assert result == "gone"

    def test_single_segment_resolve(self) -> None:
        """resolve with one segment is equivalent to __getitem__."""
        # Arrange
        state = BaseState(total=100)

        # Act
        result = state.resolve("total")

        # Assert
        assert result == 100

    def test_single_segment_missing_returns_default(self) -> None:
        """resolve with one non-existent segment → default."""
        # Arrange
        state = BaseState(total=100)

        # Act
        result = state.resolve("missing", default=0)

        # Assert
        assert result == 0
        assert result == 0
