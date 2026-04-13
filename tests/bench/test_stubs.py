# tests/bench/test_stubs.py
"""
Tests for context stubs: UserInfoStub, RuntimeInfoStub, RequestInfoStub, ContextStub.

Stubs provide sensible defaults for all context components so that tests can
create a valid Context in one line. Every stub returns a real domain object
(UserInfo, RuntimeInfo, RequestInfo, Context) — not a mock or subclass —
so isinstance checks pass throughout the system.

Scenarios covered:
    - Each stub returns the correct real type.
    - Default values match documented defaults.
    - Every field can be overridden via keyword arguments.
    - ContextStub composes three sub-stubs with independent overrides.
    - ContextStub with no arguments produces fully valid defaults.
    - Extra kwargs are forwarded where the underlying model supports them.
"""


from action_machine.intents.context.context import Context
from action_machine.intents.context.request_info import RequestInfo
from action_machine.intents.context.runtime_info import RuntimeInfo
from action_machine.intents.context.user_info import UserInfo
from action_machine.testing import StubTesterRole
from action_machine.testing.stubs import (
    ContextStub,
    RequestInfoStub,
    RuntimeInfoStub,
    UserInfoStub,
)
from tests.scenarios.domain_model.roles import AdminRole, ManagerRole

# ═════════════════════════════════════════════════════════════════════════════
# UserInfoStub
# ═════════════════════════════════════════════════════════════════════════════


class TestUserInfoStub:
    """Verify UserInfoStub defaults and overrides."""

    def test_returns_real_user_info(self) -> None:
        """The stub returns an actual UserInfo instance, not a subclass or mock."""
        user = UserInfoStub()
        assert isinstance(user, UserInfo)

    def test_default_user_id(self) -> None:
        """Default user_id is 'test_user'."""
        user = UserInfoStub()
        assert user.user_id == "test_user"

    def test_default_roles(self) -> None:
        """Default roles tuple is (StubTesterRole,)."""
        user = UserInfoStub()
        assert user.roles == (StubTesterRole,)

    def test_override_user_id(self) -> None:
        """user_id can be overridden to any string value."""
        user = UserInfoStub(user_id="admin_1")
        assert user.user_id == "admin_1"

    def test_override_roles(self) -> None:
        """roles can be overridden to a tuple of BaseRole subclasses."""
        user = UserInfoStub(roles=(AdminRole, ManagerRole))
        assert user.roles == (AdminRole, ManagerRole)

    def test_empty_roles(self) -> None:
        """Explicitly passing an empty tuple produces a user with no roles."""
        user = UserInfoStub(roles=())
        assert user.roles == ()


# ═════════════════════════════════════════════════════════════════════════════
# RuntimeInfoStub
# ═════════════════════════════════════════════════════════════════════════════


class TestRuntimeInfoStub:
    """Verify RuntimeInfoStub defaults and overrides."""

    def test_returns_real_runtime_info(self) -> None:
        """The stub returns an actual RuntimeInfo instance."""
        runtime = RuntimeInfoStub()
        assert isinstance(runtime, RuntimeInfo)

    def test_default_hostname(self) -> None:
        """Default hostname is 'test-host'."""
        runtime = RuntimeInfoStub()
        assert runtime.hostname == "test-host"

    def test_default_service_name(self) -> None:
        """Default service_name is 'test-service'."""
        runtime = RuntimeInfoStub()
        assert runtime.service_name == "test-service"

    def test_default_service_version(self) -> None:
        """Default service_version is '0.0.1'."""
        runtime = RuntimeInfoStub()
        assert runtime.service_version == "0.0.1"

    def test_override_hostname(self) -> None:
        """hostname can be overridden."""
        runtime = RuntimeInfoStub(hostname="prod-01")
        assert runtime.hostname == "prod-01"

    def test_override_service_version(self) -> None:
        """service_version can be overridden."""
        runtime = RuntimeInfoStub(service_version="2.3.0")
        assert runtime.service_version == "2.3.0"


# ═════════════════════════════════════════════════════════════════════════════
# RequestInfoStub
# ═════════════════════════════════════════════════════════════════════════════


class TestRequestInfoStub:
    """Verify RequestInfoStub defaults and overrides."""

    def test_returns_real_request_info(self) -> None:
        """The stub returns an actual RequestInfo instance."""
        request = RequestInfoStub()
        assert isinstance(request, RequestInfo)

    def test_default_trace_id(self) -> None:
        """Default trace_id is 'test-trace-000'."""
        request = RequestInfoStub()
        assert request.trace_id == "test-trace-000"

    def test_default_request_path(self) -> None:
        """Default request_path is '/test'."""
        request = RequestInfoStub()
        assert request.request_path == "/test"

    def test_default_protocol(self) -> None:
        """Default protocol is 'test'."""
        request = RequestInfoStub()
        assert request.protocol == "test"

    def test_default_request_method(self) -> None:
        """Default request_method is 'TEST'."""
        request = RequestInfoStub()
        assert request.request_method == "TEST"

    def test_override_trace_id(self) -> None:
        """trace_id can be overridden."""
        request = RequestInfoStub(trace_id="trace-abc-123")
        assert request.trace_id == "trace-abc-123"

    def test_override_protocol(self) -> None:
        """protocol can be overridden."""
        request = RequestInfoStub(protocol="https")
        assert request.protocol == "https"


# ═════════════════════════════════════════════════════════════════════════════
# ContextStub
# ═════════════════════════════════════════════════════════════════════════════


class TestContextStub:
    """Verify ContextStub composition and defaults."""

    def test_returns_real_context(self) -> None:
        """The stub returns an actual Context instance."""
        ctx = ContextStub()
        assert isinstance(ctx, Context)

    def test_default_user(self) -> None:
        """Default context user has user_id='test_user' and StubTesterRole."""
        ctx = ContextStub()
        assert ctx.user.user_id == "test_user"
        assert ctx.user.roles == (StubTesterRole,)

    def test_default_runtime(self) -> None:
        """Default context runtime has hostname='test-host'."""
        ctx = ContextStub()
        assert ctx.runtime.hostname == "test-host"

    def test_default_request(self) -> None:
        """Default context request has trace_id='test-trace-000'."""
        ctx = ContextStub()
        assert ctx.request.trace_id == "test-trace-000"

    def test_override_user(self) -> None:
        """Passing a custom UserInfoStub overrides only the user component."""
        ctx = ContextStub(user=UserInfoStub(user_id="admin", roles=(AdminRole,)))

        # Overridden component
        assert ctx.user.user_id == "admin"
        assert ctx.user.roles == (AdminRole,)

        # Other components keep defaults
        assert ctx.runtime.hostname == "test-host"
        assert ctx.request.trace_id == "test-trace-000"

    def test_override_request(self) -> None:
        """Passing a custom RequestInfoStub overrides only the request component."""
        ctx = ContextStub(request=RequestInfoStub(trace_id="my-trace"))
        assert ctx.request.trace_id == "my-trace"
        assert ctx.user.user_id == "test_user"

    def test_override_runtime(self) -> None:
        """Passing a custom RuntimeInfoStub overrides only the runtime component."""
        ctx = ContextStub(runtime=RuntimeInfoStub(hostname="prod-server"))
        assert ctx.runtime.hostname == "prod-server"
        assert ctx.user.user_id == "test_user"

    def test_all_overrides(self) -> None:
        """All three components can be overridden simultaneously."""
        ctx = ContextStub(
            user=UserInfoStub(user_id="u1", roles=()),
            request=RequestInfoStub(trace_id="t1"),
            runtime=RuntimeInfoStub(hostname="h1"),
        )
        assert ctx.user.user_id == "u1"
        assert ctx.request.trace_id == "t1"
        assert ctx.runtime.hostname == "h1"
