# tests/intents/context_requires/test_context.py
"""Tests Context is the root object of the action execution context.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Context is the root object that combines UserInfo, RequestInfo and RuntimeInfo.
Passed to the machine when run() is called and is available to aspects via ContextView,
plugins via event.context, logging templates via {%context.*}.

Context inherits BaseSchema, which provides:
- Dict-like access: ctx["user"], ctx.get("request").
- Navigation through nested components: ctx.resolve("user.user_id"),
  ctx.resolve("request.trace_id"), ctx.resolve("runtime.hostname").

When created without arguments, all components are initialized with defaults:
UserInfo(), RequestInfo(), RuntimeInfo(). Explicit None in any component
replaced by the default instance via field_validator. This guarantees
that ctx.user, ctx.request, ctx.runtime are never None.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Creation:
    - With a full set of components - production context.
    - No arguments - all components are by default (not None).
    - With partial data - only user.
    - None components are replaced by defaults (field_validator).

BaseSchema - dict-like access:
    - __getitem__, __contains__, get, keys.

Navigation via resolve:
    - Two levels: ctx.resolve("user.user_id").
    - Three levels: ctx.resolve("user.org") through the successor of UserInfo.
    - All components: user, request, runtime.
    - Missing paths at any level.

Integration with components:
    - ctx.user - UserInfo instance.
    - ctx.request - RequestInfo instance.
    - ctx.runtime - RuntimeInfo instance.

Extension via inheritance:
    - Descendants of UserInfo, RequestInfo, RuntimeInfo with explicitly declared
      fields are used to test three-level navigation.
      This is the only way to add fields - extra="forbid" on all
      Info classes prohibit custom fields."""

from typing import Any

from pydantic import ConfigDict

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.request_info import RequestInfo
from aoa.action_machine.context.runtime_info import RuntimeInfo
from aoa.action_machine.context.user_info import UserInfo
from tests.action_machine.scenarios.domain_model.roles import AdminRole, ManagerRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
#Descendants of Info classes for testing three-level navigation.
#
#UserInfo, RequestInfo, RuntimeInfo do not have an extra field (extra="forbid").
#Extension is only through inheritance with explicitly declared fields.
# ═════════════════════════════════════════════════════════════════════════════


class _ExtendedUserInfo(UserInfo):
    """A successor to UserInfo with additional fields for tests."""
    model_config = ConfigDict(frozen=True)
    org: str | None = None
    settings: dict[str, Any] = {}


class _ExtendedRequestInfo(RequestInfo):
    """Descendant of RequestInfo with an additional field for tests."""
    model_config = ConfigDict(frozen=True)
    correlation_id: str | None = None


class _ExtendedRuntimeInfo(RuntimeInfo):
    """A successor to RuntimeInfo with an additional field for tests."""
    model_config = ConfigDict(frozen=True)
    region: str | None = None


# ═════════════════════════════════════════════════════════════════════════════
#Creation and initialization
# ═════════════════════════════════════════════════════════════════════════════


class TestContextCreation:
    """Creating a Context with different combinations of components."""

    def test_create_full(self) -> None:
        """Context with a full set of components - production context.

        AuthCoordinator.process() creates a Context with the authenticated
        user, request metadata, and environment information."""
        #Arrange - all three components
        user = UserInfo(user_id="agent_007", roles=(AdminRole,))
        request = RequestInfo(trace_id="trace-123", request_path="/api/v1/orders")
        runtime = RuntimeInfo(hostname="pod-xyz", service_name="order-service")

        #Act - creating a full context
        ctx = Context(user=user, request=request, runtime=runtime)

        #Assert - all components are installed
        assert ctx.user is user
        assert ctx.request is request
        assert ctx.runtime is runtime

    def test_create_default(self) -> None:
        """Context without arguments - all components are created by default.

        Ensures that ctx.user, ctx.request, ctx.runtime never
        are not equal to None - always valid objects with default values."""
        #Arrange & Act - no arguments
        ctx = Context()

        #Assert - components are not None, but default instances
        assert ctx.user is not None
        assert ctx.request is not None
        assert ctx.runtime is not None
        assert isinstance(ctx.user, UserInfo)
        assert isinstance(ctx.request, RequestInfo)
        assert isinstance(ctx.runtime, RuntimeInfo)

    def test_create_default_user_values(self) -> None:
        """Context() creates UserInfo with defaults: user_id=None, roles=().
        This is an anonymous context created by NoAuthCoordinator."""
        # Arrange & Act
        ctx = Context()

        #Assert - default UserInfo
        assert ctx.user.user_id is None
        assert ctx.user.roles == ()

    def test_create_with_user_only(self) -> None:
        """Context with only user - request and runtime are created by default."""
        # Arrange
        user = UserInfo(user_id="u1", roles=(ManagerRole,))

        #Act - user only
        ctx = Context(user=user)

        #Assert - user is specified, the rest is default
        assert ctx.user.user_id == "u1"
        assert ctx.request is not None
        assert ctx.runtime is not None
        assert ctx.request.trace_id is None
        assert ctx.runtime.hostname is None

    def test_none_components_replaced_with_defaults(self) -> None:
        """An explicit None in the component is replaced with the default instance.

        Context(user=None) is equivalent to Context() - user will be
        UserInfo() with defaults, not None. Implemented via
        field_validator("user", mode="before") in the Context model."""
        #Arrange & Act - explicit None
        ctx = Context(user=None, request=None, runtime=None)

        #Assert - None replaced with default objects
        assert ctx.user is not None
        assert ctx.request is not None
        assert ctx.runtime is not None
        assert isinstance(ctx.user, UserInfo)
        assert isinstance(ctx.request, RequestInfo)
        assert isinstance(ctx.runtime, RuntimeInfo)


# ═════════════════════════════════════════════════════════════════════════════
#BaseSchema - dict-like access
# ═════════════════════════════════════════════════════════════════════════════


class TestContextDictAccess:
    """Dict-like access to Context components via BaseSchema."""

    def test_getitem_user(self) -> None:
        """ctx["user"] → UserInfo object.

        BaseSchema.__getitem__ delegates to getattr(self, "user")."""
        # Arrange
        user = UserInfo(user_id="u1")
        ctx = Context(user=user)

        #Act & Assert - access through brackets returns the same object
        assert ctx["user"] is user

    def test_getitem_request(self) -> None:
        """ctx["request"] → RequestInfo object."""
        # Arrange
        request = RequestInfo(trace_id="t1")
        ctx = Context(request=request)

        # Act & Assert
        assert ctx["request"] is request

    def test_getitem_runtime(self) -> None:
        """ctx["runtime"] → RuntimeInfo object."""
        # Arrange
        runtime = RuntimeInfo(hostname="h1")
        ctx = Context(runtime=runtime)

        # Act & Assert
        assert ctx["runtime"] is runtime

    def test_contains(self) -> None:
        """
        "user" in ctx → True; "nonexistent" in ctx → False.
        """
        # Arrange
        ctx = Context()

        # Act & Assert
        assert "user" in ctx
        assert "request" in ctx
        assert "runtime" in ctx
        assert "nonexistent" not in ctx

    def test_get(self) -> None:
        """
        ctx.get("user") → UserInfo; ctx.get("missing") → None.
        """
        # Arrange
        ctx = Context(user=UserInfo(user_id="u1"))

        # Act & Assert
        assert ctx.get("user") is not None
        assert ctx.get("user").user_id == "u1"
        assert ctx.get("nonexistent") is None
        assert ctx.get("nonexistent", "fallback") == "fallback"

    def test_keys(self) -> None:
        """keys() contains user, request, runtime.

        Context stores three components as pydantic fields.
        BaseSchema.keys() returns model_fields.keys()."""
        # Arrange
        ctx = Context()

        # Act
        keys = ctx.keys()

        #Assert - three components are present
        assert "user" in keys
        assert "request" in keys
        assert "runtime" in keys


# ═════════════════════════════════════════════════════════════════════════════
#Navigation through resolve - two levels
# ═════════════════════════════════════════════════════════════════════════════


class TestContextResolveTwoLevels:
    """resolve through two levels: Context → component → field."""

    def test_resolve_user_id(self) -> None:
        """resolve("user.user_id") - Context → UserInfo → user_id.

        First step: BaseSchema.__getitem__(ctx, "user") → UserInfo.
        Second step: BaseSchema.__getitem__(UserInfo, "user_id") → "agent_007"."""
        # Arrange
        ctx = Context(user=UserInfo(user_id="agent_007"))

        # Act
        result = ctx.resolve("user.user_id")

        # Assert
        assert result == "agent_007"

    def test_resolve_user_roles(self) -> None:
        """resolve("user.roles") → tuple of role types."""
        # Arrange
        ctx = Context(user=UserInfo(roles=(AdminRole, UserRole)))

        # Act
        result = ctx.resolve("user.roles")

        # Assert
        assert result == (AdminRole, UserRole)

    def test_resolve_request_trace_id(self) -> None:
        """
        resolve("request.trace_id") — Context → RequestInfo → trace_id.
        """
        # Arrange
        ctx = Context(request=RequestInfo(trace_id="trace-abc"))

        # Act
        result = ctx.resolve("request.trace_id")

        # Assert
        assert result == "trace-abc"

    def test_resolve_request_path(self) -> None:
        """resolve("request.request_path") → request path."""
        # Arrange
        ctx = Context(request=RequestInfo(request_path="/api/v1/orders"))

        # Act
        result = ctx.resolve("request.request_path")

        # Assert
        assert result == "/api/v1/orders"

    def test_resolve_runtime_hostname(self) -> None:
        """
        resolve("runtime.hostname") — Context → RuntimeInfo → hostname.
        """
        # Arrange
        ctx = Context(runtime=RuntimeInfo(hostname="pod-xyz-42"))

        # Act
        result = ctx.resolve("runtime.hostname")

        # Assert
        assert result == "pod-xyz-42"

    def test_resolve_runtime_service_name(self) -> None:
        """resolve("runtime.service_name") → service name."""
        # Arrange
        ctx = Context(runtime=RuntimeInfo(service_name="order-service"))

        # Act
        result = ctx.resolve("runtime.service_name")

        # Assert
        assert result == "order-service"


# ═════════════════════════════════════════════════════════════════════════════
#Navigation through resolve - three levels (via inheritors of Info classes)
# ═════════════════════════════════════════════════════════════════════════════


class TestContextResolveThreeLevels:
    """resolve through three levels: Context → successor Info → successor field.

    UserInfo, RequestInfo, RuntimeInfo do not have an extra field (extra="forbid").
    Three-level navigation is tested through descendants with explicit
    declared fields - the only way to expand in a new
    architecture."""

    def test_resolve_user_extended_field(self) -> None:
        """resolve("user.org") - Context → _ExtendedUserInfo → org.

        Three levels: BaseSchema (Context) → BaseSchema (_ExtendedUserInfo)
        → field value."""
        #Arrange is a successor to UserInfo with the org field
        ctx = Context(user=_ExtendedUserInfo(org="acme"))

        # Act
        result = ctx.resolve("user.org")

        # Assert
        assert result == "acme"

    def test_resolve_request_extended_field(self) -> None:
        """
        resolve("request.correlation_id") — Context → _ExtendedRequestInfo
        → correlation_id.
        """
        #Arrange - successor of RequestInfo with the correlation_id field
        ctx = Context(request=_ExtendedRequestInfo(correlation_id="corr-001"))

        # Act
        result = ctx.resolve("request.correlation_id")

        # Assert
        assert result == "corr-001"

    def test_resolve_runtime_extended_field(self) -> None:
        """
        resolve("runtime.region") — Context → _ExtendedRuntimeInfo → region.
        """
        #Arrange is a successor of RuntimeInfo with the region field
        ctx = Context(runtime=_ExtendedRuntimeInfo(region="eu-west-1"))

        # Act
        result = ctx.resolve("runtime.region")

        # Assert
        assert result == "eu-west-1"

    def test_resolve_deep_nested_dict_field(self) -> None:
        """resolve("user.settings.theme") - four levels of navigation.

        Context → _ExtendedUserInfo → settings (dict) → theme (value).
        Navigation switches from __getitem__ (BaseSchema) strategy
        for direct access by key (dict)."""
        #Arrange is a successor to UserInfo with a settings (dict) field
        ctx = Context(user=_ExtendedUserInfo(
            settings={"theme": "dark", "lang": "ru"},
        ))

        # Act
        result = ctx.resolve("user.settings.theme")

        # Assert
        assert result == "dark"


# ═════════════════════════════════════════════════════════════════════════════
#Navigation via resolve - missing paths
# ═════════════════════════════════════════════════════════════════════════════


class TestContextResolveMissing:
    """resolve returns default for missing paths."""

    def test_missing_component_attribute(self) -> None:
        """resolve("user.nonexistent") - the attribute does not exist in UserInfo."""
        # Arrange
        ctx = Context(user=UserInfo(user_id="u1"))

        # Act
        result = ctx.resolve("user.nonexistent", default="N/A")

        # Assert
        assert result == "N/A"

    def test_missing_intermediate(self) -> None:
        """resolve("user.nonexistent.deep") - intermediate attribute not found.

        The chain is interrupted at "nonexistent", the remaining segments
        are not processed."""
        # Arrange
        ctx = Context()

        # Act
        result = ctx.resolve("user.nonexistent.deep", default="fallback")

        # Assert
        assert result == "fallback"

    def test_missing_extended_field_key(self) -> None:
        """resolve("user.settings.missing_key") - the key does not exist in the dict.

        _ExtendedUserInfo has a settings: dict field. Navigation reaches
        to dict, but the key "missing_key" is missing → default."""
        #Arrange - successor to UserInfo with the settings field
        ctx = Context(user=_ExtendedUserInfo(
            settings={"org": "acme"},
        ))

        # Act
        result = ctx.resolve("user.settings.missing_key", default="none")

        # Assert
        assert result == "none"

    def test_missing_top_level(self) -> None:
        """resolve("nonexistent") - the attribute does not exist on the Context."""
        # Arrange
        ctx = Context()

        # Act
        result = ctx.resolve("nonexistent")

        #Assert - None by default
        assert result is None

    def test_missing_without_default(self) -> None:
        """resolve("user.nonexistent") without default → None.

        resolve never throws an exception - template safe
        logging."""
        # Arrange
        ctx = Context()

        # Act
        result = ctx.resolve("user.nonexistent")

        # Assert
        assert result is None
        assert result is None
