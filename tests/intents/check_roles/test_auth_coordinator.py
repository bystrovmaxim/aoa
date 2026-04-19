# tests/intents/check_roles/test_auth_coordinator.py
"""The AuthCoordinator and NoAuthCoordinator tests are authentication coordinators.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

AuthCoordinator - coordinator of the full authentication cycle. Unites
three components in a daisy chain:

    CredentialExtractor.extract(request) → credentials
    Authenticator.authenticate(credentials) → UserInfo
    ContextAssembler.assemble(request) → RequestInfo metadata

Result - Context with authenticated user and metadata
request. If any step returns None/empty result - the entire process
returns None (authentication failed).

NoAuthCoordinator is a provider for open APIs. Always returns
anonymous Context without user and roles. Implements the same interface
(async process(request_data) → Context) same as AuthCoordinator.

Both coordinators are passed to BaseAdapter as a required parameter
auth_coordinator. The developer cannot “forget” to enable authentication -
for public APIs, NoAuthCoordinator is used as an explicit declaration.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
SCENARIOS COVERED
═══════════════════ ════════════════════ ════════════════════ ════════════════════

AuthCoordinator - successful authentication:
    - All three components return data → Context with UserInfo and RequestInfo.

AuthCoordinator - unsuccessful authentication:
    - Extractor returns empty dict → None (no credentials).
    - Authenticator returns None → None (credentials are invalid).

NoAuthCoordinator:
    - Always returns Context (not None).
    - UserInfo: user_id=None, roles=().
    - Ignores request_data.

Interface Compatibility:
    - Both coordinators have async process(request_data) → Context|None."""

import pytest

from action_machine.auth.auth_coordinator import (
    AuthCoordinator,
    ContextAssembler,
    CredentialExtractor,
    NoAuthCoordinator,
)
from action_machine.auth.authenticator import Authenticator
from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from tests.scenarios.domain_model.roles import AdminRole, SpyRole

# ═════════════════════════════════════════════════════════════════════════════
#Mock implementations of authentication components
# ═════════════════════════════════════════════════════════════════════════════


class _MockExtractor(CredentialExtractor):
    """A mock extractor that returns the given credentials.

    If credentials_to_return is an empty dict, simulates the situation
    "credentials not found in request" (for example, no header
    Authorization)."""

    def __init__(self, credentials_to_return: dict | None = None):
        self._credentials = credentials_to_return if credentials_to_return is not None else {}

    async def extract(self, request_data):
        return self._credentials


class _MockAuthenticator(Authenticator):
    """Mock authenticator that returns the given UserInfo.

    If user_to_return=None, simulates invalid credentials
    (for example, an expired token)."""

    def __init__(self, user_to_return: UserInfo | None = None):
        self._user = user_to_return

    async def authenticate(self, credentials):
        return self._user


class _MockAssembler(ContextAssembler):
    """Mock request metadata collector.

    Returns a fixed dictionary with trace_id, request_path
    and other fields to create RequestInfo."""

    def __init__(self, metadata_to_return: dict | None = None):
        self._metadata = metadata_to_return or {
            "trace_id": "test-trace-001",
            "request_path": "/api/v1/test",
        }

    async def assemble(self, request_data):
        return self._metadata


# ═════════════════════════════════════════════════════════════════════════════
#AuthCoordinator - successful authentication
# ═════════════════════════════════════════════════════════════════════════════


class TestAuthCoordinatorSuccess:
    """Full authentication cycle - all components return data."""

    @pytest.mark.asyncio
    async def test_full_cycle_returns_context(self) -> None:
        """All three components return data → Context with UserInfo and RequestInfo.

        Chain:
        1. Extractor.extract() → {"api_key": "secret-123"}
        2. Authenticator.authenticate(credentials) → UserInfo(user_id="u1", roles=(AdminRole,))
        3. Assembler.assemble() → {"trace_id": "t1", "request_path": "/api"}
        4. Result → Context(user=UserInfo, request=RequestInfo)"""
        #Arrange - three components with valid data
        extractor = _MockExtractor({"api_key": "secret-123"})
        authenticator = _MockAuthenticator(
            UserInfo(user_id="u1", roles=(AdminRole,)),
        )
        assembler = _MockAssembler({
            "trace_id": "trace-full",
            "request_path": "/api/v1/orders",
        })

        coordinator = AuthCoordinator(
            extractor=extractor,
            auth_instance=authenticator,
            assembler=assembler,
        )

        #Act - full authentication cycle
        result = await coordinator.process({"raw_request": "data"})

        #Assert - Context contains the authenticated user
        assert result is not None
        assert isinstance(result, Context)
        assert result.user.user_id == "u1"
        assert result.user.roles == (AdminRole,)
        assert result.request.trace_id == "trace-full"
        assert result.request.request_path == "/api/v1/orders"

    @pytest.mark.asyncio
    async def test_user_info_preserved_in_context(self) -> None:
        """UserInfo from Authenticator is passed to Context unchanged.
        All UserInfo fields (user_id, roles) are accessible through context.user."""
        #Arrange - UserInfo with user_id and roles
        user = UserInfo(user_id="agent_007", roles=(SpyRole,))
        extractor = _MockExtractor({"token": "valid"})
        authenticator = _MockAuthenticator(user)
        assembler = _MockAssembler()
        coordinator = AuthCoordinator(
            extractor=extractor,
            auth_instance=authenticator,
            assembler=assembler,
        )

        # Act
        result = await coordinator.process(None)

        #Assert - UserInfo is completely saved
        assert result is not None
        assert result.user.user_id == "agent_007"
        assert result.user.roles == (SpyRole,)


# ═════════════════════════════════════════════════════════════════════════════
#AuthCoordinator - failed authentication
# ═════════════════════════════════════════════════════════════════════════════


class TestAuthCoordinatorFailure:
    """Authentication was interrupted at one of the steps → None."""

    @pytest.mark.asyncio
    async def test_empty_credentials_returns_none(self) -> None:
        """Extractor returns an empty dict → process() returns None.

        Empty credentials mean the request contains no data
        authentication (no Authorization header, no cookie, etc.).
        Authenticator is not called."""
        #Arrange - extractor returns empty dict
        extractor = _MockExtractor({})
        authenticator = _MockAuthenticator(UserInfo(user_id="should_not_reach"))
        assembler = _MockAssembler()

        coordinator = AuthCoordinator(
            extractor=extractor,
            auth_instance=authenticator,
            assembler=assembler,
        )

        #Act - the process is interrupted at the first step
        result = await coordinator.process(None)

        #Assert - None, authentication failed
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticator_returns_none(self) -> None:
        """Authenticator returns None → process() returns None.

        Credentials have been transferred, but are invalid (expired token,
        incorrect password, blocked account). Assembler is not called."""
        #Arrange — extractor returns credentials, authenticator → None
        extractor = _MockExtractor({"token": "expired-token"})
        authenticator = _MockAuthenticator(None)
        assembler = _MockAssembler()

        coordinator = AuthCoordinator(
            extractor=extractor,
            auth_instance=authenticator,
            assembler=assembler,
        )

        #Act - the process is interrupted at the second step
        result = await coordinator.process(None)

        #Assert — None, credentials are invalid
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# NoAuthCoordinator
# ═════════════════════════════════════════════════════════════════════════════


class TestNoAuthCoordinator:
    """NoAuthCoordinator - An anonymous context for public APIs."""

    @pytest.mark.asyncio
    async def test_returns_context_not_none(self) -> None:
        """NoAuthCoordinator.process() always returns Context (not None).

        Unlike AuthCoordinator which can return None
        if authentication fails, NoAuthCoordinator guarantees
        Context for each request."""
        # Arrange
        coordinator = NoAuthCoordinator()

        # Act
        result = await coordinator.process({"any": "data"})

        #Assert - always Context, not None
        assert result is not None
        assert isinstance(result, Context)

    @pytest.mark.asyncio
    async def test_anonymous_user(self) -> None:
        """NoAuthCoordinator creates an anonymous user.

        UserInfo: user_id=None, roles=(). Actions with @check_roles(NoneRole)
        are checked, actions with specific roles are rejected."""
        # Arrange
        coordinator = NoAuthCoordinator()

        # Act
        result = await coordinator.process(None)

        #Assert - anonymous user
        assert result.user.user_id is None
        assert result.user.roles == ()

    @pytest.mark.asyncio
    async def test_ignores_request_data(self) -> None:
        """NoAuthCoordinator ignores request_data.

        Call process() with any argument (None, dict, string)
        returns the same anonymous Context."""
        # Arrange
        coordinator = NoAuthCoordinator()

        #Act - different types of request_data
        result_none = await coordinator.process(None)
        result_dict = await coordinator.process({"key": "value"})
        result_str = await coordinator.process("raw_request")

        #Assert - all three return an anonymous Context
        assert result_none.user.user_id is None
        assert result_dict.user.user_id is None
        assert result_str.user.user_id is None

    @pytest.mark.asyncio
    async def test_each_call_returns_new_context(self) -> None:
        """Each call to process() returns a new Context instance.

        Contexts are not shared between requests - complete isolation."""
        # Arrange
        coordinator = NoAuthCoordinator()

        #Act - two calls
        ctx1 = await coordinator.process(None)
        ctx2 = await coordinator.process(None)

        #Assert - two different objects
        assert ctx1 is not ctx2


# ═════════════════════════════════════════════════════════════════════════════
#Interface compatibility
# ═════════════════════════════════════════════════════════════════════════════


class TestInterfaceCompatibility:
    """Both coordinators have the same process() interface."""

    def test_auth_coordinator_has_process(self) -> None:
        """AuthCoordinator has an asynchronous process() method."""
        # Arrange
        coordinator = AuthCoordinator(
            extractor=_MockExtractor(),
            auth_instance=_MockAuthenticator(),
            assembler=_MockAssembler(),
        )

        #Act & Assert - the method exists
        assert hasattr(coordinator, "process")
        assert callable(coordinator.process)

    def test_no_auth_coordinator_has_process(self) -> None:
        """NoAuthCoordinator has an asynchronous process() method."""
        # Arrange
        coordinator = NoAuthCoordinator()

        #Act & Assert - the method exists
        assert hasattr(coordinator, "process")
        assert callable(coordinator.process)

    @pytest.mark.asyncio
    async def test_both_accept_any_request_data(self) -> None:
        """Both coordinators accept arbitrary request_data.

        process() accepts Any - the type depends on the protocol:
        FastAPI Request, MCP tool call dict, None, etc."""
        # Arrange
        auth = AuthCoordinator(
            extractor=_MockExtractor({"key": "val"}),
            auth_instance=_MockAuthenticator(UserInfo(user_id="u1")),
            assembler=_MockAssembler(),
        )
        no_auth = NoAuthCoordinator()

        #Act - both accept None
        auth_result = await auth.process(None)
        no_auth_result = await no_auth.process(None)

        #Assert - both returned a result
        assert auth_result is not None
        assert no_auth_result is not None
        assert no_auth_result is not None
