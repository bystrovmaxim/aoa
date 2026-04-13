# tests/intents/context/test_context_view.py
"""
Tests for ContextView — frozen object with controlled access to context fields.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

ContextView is the supported way to read context data from aspects and error
handlers. The machine builds it for methods decorated with @context_requires.
It exposes get(key), which checks the key is in the allowed set and delegates
to context.resolve(key).

Access to a non-allowed key → ContextAccessError.

═══════════════════════════════════════════════════════════════════════════════
COVERED SCENARIOS
═══════════════════════════════════════════════════════════════════════════════

Allowed access:
    - user.user_id, user.roles via Ctx constants.
    - request.trace_id, runtime.hostname.
    - Several allowed keys at once.

Denied access:
    - Unregistered key → ContextAccessError.
    - Key from another component → ContextAccessError.
    - Empty allowed set → everything denied.

Missing fields:
    - Allowed key but value None → returns None.
    - Custom path, field missing → returns None.

Custom fields via Info subclasses:
    - UserInfo subclass with billing_plan.
    - RequestInfo subclass with ab_variant.

Frozen semantics:
    - Setting attributes forbidden.
    - Deleting attributes forbidden.

Introspection:
    - allowed_keys returns frozenset.
    - repr includes key names.
"""


import pytest
from pydantic import ConfigDict

from action_machine.intents.context.context import Context
from action_machine.intents.context.context_view import ContextView
from action_machine.intents.context.ctx_constants import Ctx
from action_machine.intents.context.request_info import RequestInfo
from action_machine.intents.context.runtime_info import RuntimeInfo
from action_machine.intents.context.user_info import UserInfo
from action_machine.model.exceptions import ContextAccessError
from tests.scenarios.domain_model.roles import AdminRole, ManagerRole, UserRole

# ═════════════════════════════════════════════════════════════════════════════
# Info subclasses for custom-field tests.
#
# UserInfo, RequestInfo, RuntimeInfo have no extra/tags (extra="forbid").
# Extend only via subclasses with explicit fields.
# ═════════════════════════════════════════════════════════════════════════════


class _BillingUserInfo(UserInfo):
    """UserInfo subclass with billing_plan for tests."""
    model_config = ConfigDict(frozen=True)
    billing_plan: str | None = None


class _TaggedRequestInfo(RequestInfo):
    """RequestInfo subclass with ab_variant for tests."""
    model_config = ConfigDict(frozen=True)
    ab_variant: str | None = None


# ═════════════════════════════════════════════════════════════════════════════
# Allowed access
# ═════════════════════════════════════════════════════════════════════════════


class TestAllowedAccess:
    """Allowed keys return correct values."""

    def test_get_user_id(self) -> None:
        """
        ContextView.get(Ctx.User.user_id) returns user_id from context.

        ContextView checks "user.user_id" is allowed and delegates to
        context.resolve("user.user_id").
        """
        # Arrange — context with user_id, view allows user.user_id
        context = Context(user=UserInfo(user_id="agent_007"))
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act — request allowed field
        result = view.get(Ctx.User.user_id)

        # Assert — value from context
        assert result == "agent_007"

    def test_get_user_roles(self) -> None:
        """
        ContextView.get(Ctx.User.roles) returns role types tuple.
        """
        # Arrange
        context = Context(user=UserInfo(roles=(AdminRole, UserRole)))
        view = ContextView(context, frozenset({Ctx.User.roles}))

        # Act
        result = view.get(Ctx.User.roles)

        # Assert
        assert result == (AdminRole, UserRole)

    def test_get_request_trace_id(self) -> None:
        """
        ContextView.get(Ctx.Request.trace_id) returns trace_id.
        """
        # Arrange
        context = Context(request=RequestInfo(trace_id="trace-abc-123"))
        view = ContextView(context, frozenset({Ctx.Request.trace_id}))

        # Act
        result = view.get(Ctx.Request.trace_id)

        # Assert
        assert result == "trace-abc-123"

    def test_get_runtime_hostname(self) -> None:
        """
        ContextView.get(Ctx.Runtime.hostname) returns hostname.
        """
        # Arrange
        context = Context(runtime=RuntimeInfo(hostname="prod-server-01"))
        view = ContextView(context, frozenset({Ctx.Runtime.hostname}))

        # Act
        result = view.get(Ctx.Runtime.hostname)

        # Assert
        assert result == "prod-server-01"

    def test_get_multiple_allowed_keys(self) -> None:
        """
        ContextView with several allowed keys — each is readable.
        """
        # Arrange
        context = Context(
            user=UserInfo(user_id="u1", roles=(ManagerRole,)),
            request=RequestInfo(client_ip="10.0.0.1"),
        )
        allowed = frozenset({Ctx.User.user_id, Ctx.User.roles, Ctx.Request.client_ip})
        view = ContextView(context, allowed)

        # Act
        user_id = view.get(Ctx.User.user_id)
        roles = view.get(Ctx.User.roles)
        ip = view.get(Ctx.Request.client_ip)

        # Assert
        assert user_id == "u1"
        assert roles == (ManagerRole,)
        assert ip == "10.0.0.1"


# ═════════════════════════════════════════════════════════════════════════════
# Denied access
# ═════════════════════════════════════════════════════════════════════════════


class TestDeniedAccess:
    """Non-allowed keys raise ContextAccessError."""

    def test_access_denied_for_unregistered_key(self) -> None:
        """
        Unregistered key → ContextAccessError.

        View allows only user.user_id but user.roles is requested.
        """
        # Arrange — only user.user_id allowed
        context = Context(user=UserInfo(user_id="u1", roles=(AdminRole,)))
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act / Assert — user.roles denied
        with pytest.raises(ContextAccessError) as exc_info:
            view.get(Ctx.User.roles)

        # Assert — message mentions key
        assert "user.roles" in str(exc_info.value)

    def test_access_denied_for_different_component(self) -> None:
        """
        Key from another component → ContextAccessError.

        Only user.user_id allowed; request.trace_id requested.
        """
        # Arrange
        context = Context(
            user=UserInfo(user_id="u1"),
            request=RequestInfo(trace_id="t1"),
        )
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act / Assert
        with pytest.raises(ContextAccessError):
            view.get(Ctx.Request.trace_id)

    def test_error_contains_key_and_allowed_keys(self) -> None:
        """
        ContextAccessError includes requested key and allowed set.
        """
        # Arrange
        context = Context()
        allowed = frozenset({Ctx.User.user_id, Ctx.Request.trace_id})
        view = ContextView(context, allowed)

        # Act
        with pytest.raises(ContextAccessError) as exc_info:
            view.get(Ctx.Runtime.hostname)

        # Assert
        error = exc_info.value
        assert error.key == "runtime.hostname"
        assert error.allowed_keys == allowed

    def test_empty_allowed_keys_denies_everything(self) -> None:
        """
        Empty allowed set — every key denied.
        """
        # Arrange
        context = Context(user=UserInfo(user_id="u1"))
        view = ContextView(context, frozenset())

        # Act / Assert
        with pytest.raises(ContextAccessError):
            view.get(Ctx.User.user_id)


# ═════════════════════════════════════════════════════════════════════════════
# Allowed key but missing field — returns None
# ═════════════════════════════════════════════════════════════════════════════


class TestNonexistentButAllowedKey:
    """Allowed key but field absent in context — returns None."""

    def test_allowed_but_none_value(self) -> None:
        """
        Allowed user.user_id, value None by default.

        Context() uses UserInfo with user_id=None. Key is allowed;
        context.resolve("user.user_id") returns None.
        """
        # Arrange
        context = Context()
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act
        result = view.get(Ctx.User.user_id)

        # Assert
        assert result is None

    def test_custom_path_not_in_context(self) -> None:
        """
        Allowed custom path but field missing.

        UserInfo has no billing_plan (no extra).
        context.resolve("user.billing_plan") returns None.
        """
        # Arrange
        context = Context(user=UserInfo())
        view = ContextView(context, frozenset({"user.billing_plan"}))

        # Act
        result = view.get("user.billing_plan")

        # Assert
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Custom fields via Info subclasses
# ═════════════════════════════════════════════════════════════════════════════


class TestCustomExtraFields:
    """
    Access custom fields via Info subclasses.

    UserInfo, RequestInfo, RuntimeInfo have no extra/tags (extra="forbid").
    Extend via subclasses with explicit fields. ContextView.get() delegates to
    context.resolve(), which walks BaseSchema objects via __getitem__.
    """

    def test_user_extended_field(self) -> None:
        """
        ContextView reads UserInfo subclass field.

        _BillingUserInfo adds billing_plan.
        context.resolve("user.billing_plan"): Context → _BillingUserInfo → billing_plan.
        """
        # Arrange
        context = Context(user=_BillingUserInfo(billing_plan="premium"))
        view = ContextView(context, frozenset({"user.billing_plan"}))

        # Act
        result = view.get("user.billing_plan")

        # Assert
        assert result == "premium"

    def test_request_extended_field(self) -> None:
        """
        ContextView reads RequestInfo subclass field.

        _TaggedRequestInfo adds ab_variant.
        """
        # Arrange
        context = Context(request=_TaggedRequestInfo(ab_variant="control"))
        view = ContextView(context, frozenset({"request.ab_variant"}))

        # Act
        result = view.get("request.ab_variant")

        # Assert
        assert result == "control"


# ═════════════════════════════════════════════════════════════════════════════
# Frozen semantics
# ═════════════════════════════════════════════════════════════════════════════


class TestFrozen:
    """ContextView is immutable — no setattr/delattr."""

    def test_setattr_raises(self) -> None:
        """New attribute → AttributeError mentioning frozen."""
        # Arrange
        context = Context()
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act / Assert
        with pytest.raises(AttributeError, match="frozen"):
            view.x = 42  # type: ignore[attr-defined]

    def test_delattr_raises(self) -> None:
        """Deleting attribute → AttributeError mentioning frozen."""
        # Arrange
        context = Context()
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act / Assert
        with pytest.raises(AttributeError, match="frozen"):
            del view._context  # type: ignore[attr-defined]

    def test_overwrite_allowed_keys_raises(self) -> None:
        """Overwriting _allowed_keys → AttributeError mentioning frozen."""
        # Arrange
        context = Context()
        view = ContextView(context, frozenset({Ctx.User.user_id}))

        # Act / Assert
        with pytest.raises(AttributeError, match="frozen"):
            view._allowed_keys = frozenset()  # type: ignore[misc]


# ═════════════════════════════════════════════════════════════════════════════
# Introspection
# ═════════════════════════════════════════════════════════════════════════════


class TestAllowedKeysProperty:
    """allowed_keys for introspection."""

    def test_returns_frozenset(self) -> None:
        """allowed_keys returns the same frozenset passed at construction."""
        # Arrange
        allowed = frozenset({Ctx.User.user_id, Ctx.Request.trace_id})
        context = Context()
        view = ContextView(context, allowed)

        # Act
        result = view.allowed_keys

        # Assert
        assert result == allowed
        assert isinstance(result, frozenset)

    def test_empty_allowed_keys(self) -> None:
        """Empty allowed set is valid."""
        # Arrange
        context = Context()
        view = ContextView(context, frozenset())

        # Act / Assert
        assert view.allowed_keys == frozenset()


# ═════════════════════════════════════════════════════════════════════════════
# String representation
# ═════════════════════════════════════════════════════════════════════════════


class TestRepr:
    """repr for debugging."""

    def test_repr_contains_keys(self) -> None:
        """repr includes class name and allowed key names."""
        # Arrange
        context = Context()
        view = ContextView(context, frozenset({Ctx.User.user_id, Ctx.User.roles}))

        # Act
        result = repr(view)

        # Assert
        assert "ContextView" in result
        assert "user.user_id" in result
        assert "user.roles" in result

    def test_repr_empty_keys(self) -> None:
        """repr with empty key set."""
        # Arrange
        context = Context()
        view = ContextView(context, frozenset())

        # Act
        result = repr(view)

        # Assert
        assert "ContextView" in result
