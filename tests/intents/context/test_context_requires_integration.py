# tests/intents/context/test_context_requires_integration.py
"""Integration tests @context_requires - full run of Action through
TestBench with testing of ContextView passing to aspects and error handlers.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
PURPOSE
═══════════════════ ════════════════════ ════════════════════ ════════════════════

Checks that aspects and error handlers only receive ContextView with
context fields explicitly requested by @context_requires on the method.

All core types (Params, Result, State) are frozen. Results are generated via
constructor, and not through mutation after creation.

═══════════════════ ════════════════════ ════════════════════ ════════════════════
TESTABLE SCENARIOS
═══════════════════ ════════════════════ ════════════════════ ════════════════════

- The aspect with @context_requires gets the ContextView and reads the user_id.
- An aspect without @context_requires works with a standard signature (5 parameters).
- Access to an unsolicited context field → ContextAccessError.
- The error handler with @context_requires gets its ContextView.
- Error handler without @context_requires works with standard signature.
- Summary aspect with @context_requires gets ContextView.
- ToolsBox does not provide public access to the context."""

import pytest
from pydantic import Field

from action_machine.context.ctx_constants import Ctx
from action_machine.intents.aspects.regular_aspect_decorator import regular_aspect
from action_machine.intents.aspects.summary_aspect_decorator import summary_aspect
from action_machine.intents.check_roles import NoneRole, check_roles
from action_machine.intents.checkers import result_string
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.intents.meta.meta_decorator import meta
from action_machine.intents.on_error import on_error
from action_machine.model.base_action import BaseAction
from action_machine.model.base_params import BaseParams
from action_machine.model.base_result import BaseResult
from action_machine.exceptions import ContextAccessError
from action_machine.testing import TestBench
from tests.scenarios.domain_model.domains import TestDomain
from tests.scenarios.domain_model.roles import AdminRole

# ═════════════════════════════════════════════════════════════════════════════
#Test Models Params and Result (frozen as required)
# ═════════════════════════════════════════════════════════════════════════════


class _IntegrationParams(BaseParams):
    """Parameters for integration tests context_requires."""
    name: str = Field(description="Name to test")


class _IntegrationResult(BaseResult):
    """The result for integration tests context_requires is frozen."""
    message: str = Field(description="Result message")


class _BoxCheckResult(BaseResult):
    """Result for checking if box.context is missing."""
    has_context: bool = Field(description="Does ToolsBox have a context property")


class _BoxCheckParams(BaseParams):
    """Concrete params for :class:`_BoxCheckAction` (interchange graph needs a params node)."""


# ═════════════════════════════════════════════════════════════════════════════
#Test Action
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Action with aspect reading user_id from context", domain=TestDomain)
@check_roles(NoneRole)
class _CtxReadAction(BaseAction[_IntegrationParams, _IntegrationResult]):
    """The aspect with @context_requires reads the user_id and writes it to the result.
    The result is created through the constructor (frozen)."""

    @regular_aspect("Reading the context")
    @result_string("ctx_user_id", required=True)
    @context_requires(Ctx.User.user_id)
    async def read_ctx_aspect(self, params, state, box, connections, ctx):
        user_id = ctx.get(Ctx.User.user_id)
        return {"ctx_user_id": str(user_id)}

    @summary_aspect("Formation of the result")
    async def build_summary(self, params, state, box, connections):
        #Create a frozen result using the constructor
        return _IntegrationResult(message=f"user={state['ctx_user_id']}")


@meta(description="Action without @context_requires - standard signature", domain=TestDomain)
@check_roles(NoneRole)
class _NoCtxAction(BaseAction[_IntegrationParams, _IntegrationResult]):
    """An aspect without @context_requires works with 5 parameters as before.
    The result is created through the constructor."""

    @summary_aspect("Simple result")
    async def build_summary(self, params, state, box, connections):
        return _IntegrationResult(message=f"hello {params.name}")


@meta(description="Action with an aspect accessing an unsolicited field", domain=TestDomain)
@check_roles(NoneRole)
class _CtxAccessViolationAction(BaseAction[_IntegrationParams, _IntegrationResult]):
    """The aspect requests user.user_id but accesses user.roles - ContextAccessError."""

    @regular_aspect("Access Violation")
    @context_requires(Ctx.User.user_id)
    async def violate_aspect(self, params, state, box, connections, ctx):
        #Accessing an unsolicited field should throw a ContextAccessError
        ctx.get(Ctx.User.roles)
        return {}

    @summary_aspect("Bottom line")
    async def build_summary(self, params, state, box, connections):
        return _IntegrationResult(message="should not reach")


@meta(description="Action with error handler reading context", domain=TestDomain)
@check_roles(NoneRole)
class _OnErrorCtxAction(BaseAction[_IntegrationParams, _IntegrationResult]):
    """The aspect throws ValueError, the handler with @context_requires reads user_id."""

    @regular_aspect("Throws an error")
    async def failing_aspect(self, params, state, box, connections):
        raise ValueError("test error")

    @summary_aspect("Bottom line")
    async def build_summary(self, params, state, box, connections):
        return _IntegrationResult(message="should not reach")

    @on_error(ValueError, description="Processing with context")
    @context_requires(Ctx.User.user_id)
    async def handle_on_error(self, params, state, box, connections, error, ctx):
        user_id = ctx.get(Ctx.User.user_id)
        return _IntegrationResult(message=f"error handled by {user_id}")


@meta(description="Action with error handler without @context_requires", domain=TestDomain)
@check_roles(NoneRole)
class _OnErrorNoCtxAction(BaseAction[_IntegrationParams, _IntegrationResult]):
    """Aspect throws ValueError, handler without @context_requires - 6 parameters."""

    @regular_aspect("Throws an error")
    async def failing_aspect(self, params, state, box, connections):
        raise ValueError("test error")

    @summary_aspect("Bottom line")
    async def build_summary(self, params, state, box, connections):
        return _IntegrationResult(message="should not reach")

    @on_error(ValueError, description="Processing without context")
    async def handle_on_error(self, params, state, box, connections, error):
        return _IntegrationResult(message=f"error: {error}")


@meta(description="Action with summary reading context", domain=TestDomain)
@check_roles(NoneRole)
class _SummaryCtxAction(BaseAction[_IntegrationParams, _IntegrationResult]):
    """The summary aspect with @context_requires reads hostname."""

    @summary_aspect("Result with context")
    @context_requires(Ctx.Runtime.hostname)
    async def build_summary(self, params, state, box, connections, ctx):
        hostname = ctx.get(Ctx.Runtime.hostname)
        return _IntegrationResult(message=f"host={hostname}")


@meta(description="Checking for missing box.context", domain=TestDomain)
@check_roles(NoneRole)
class _BoxCheckAction(BaseAction[_BoxCheckParams, _BoxCheckResult]):
    """Checks that ToolsBox does not have a public context property."""

    @summary_aspect("Examination")
    async def check_summary(self, params, state, box, connections):
        #box.context should not exist as a public attribute
        has_context = hasattr(box, "context")
        return _BoxCheckResult(has_context=has_context)


# ═════════════════════════════════════════════════════════════════════════════
#Tests
# ═════════════════════════════════════════════════════════════════════════════


class TestAspectWithContextRequires:
    """The aspect with @context_requires gets the ContextView and reads the data."""

    @pytest.mark.asyncio
    async def test_reads_user_id_from_context(self) -> None:
        """Aspect with @context_requires(Ctx.User.user_id) gets a ContextView
        and reads the user_id from the context. The result contains the value read."""
        #Arrange - bench with user test_agent
        bench = TestBench().with_user(user_id="test_agent")
        params = _IntegrationParams(name="test")

        #Act - full run of Action, aspect reads user_id via ctx
        result = await bench.run(_CtxReadAction(), params, rollup=False)

        #Assert - user_id from the context is included in the result
        assert result.message == "user=test_agent"


class TestAspectWithoutContextRequires:
    """An aspect without @context_requires works with the standard signature."""

    @pytest.mark.asyncio
    async def test_standard_five_params(self) -> None:
        """Action without @context_requires - the aspect is called with 5 parameters,
        the result is generated from params, without access to the context."""
        #Arrange - regular bench
        bench = TestBench()
        params = _IntegrationParams(name="world")

        #Act - Action without @context_requires
        result = await bench.run(_NoCtxAction(), params, rollup=False)

        #Assert - aspect worked with 5 parameters
        assert result.message == "hello world"


class TestContextAccessViolation:
    """Accessing an unqueried field throws a ContextAccessError."""

    @pytest.mark.asyncio
    async def test_access_to_unregistered_key_raises(self) -> None:
        """The aspect requests user.user_id but accesses user.roles.
        ContextView throws ContextAccessError with the key specified."""
        #Arrange — bench with user u1, roles=(AdminRole,)
        bench = TestBench().with_user(user_id="u1", roles=(AdminRole,))
        params = _IntegrationParams(name="test")

        #Act / Assert - ContextAccessError is thrown outside
        with pytest.raises(ContextAccessError) as exc_info:
            await bench.run(_CtxAccessViolationAction(), params, rollup=False)

        #Assert - the error indicates the requested key
        assert exc_info.value.key == "user.roles"


class TestOnErrorWithContextRequires:
    """The error handler with @context_requires gets its ContextView."""

    @pytest.mark.asyncio
    async def test_error_handler_reads_context(self) -> None:
        """Error handler with @context_requires(Ctx.User.user_id) gets
        separate ContextView (independent of the aspect that crashed)."""
        #Arrange - bench with user error_handler_user
        bench = TestBench().with_user(user_id="error_handler_user")
        params = _IntegrationParams(name="test")

        #Act - aspect throws ValueError, handler reads user_id via ctx
        result = await bench.run(_OnErrorCtxAction(), params, rollup=False)

        #Assert - the handler read the user_id from the context
        assert result.message == "error handled by error_handler_user"


class TestOnErrorWithoutContextRequires:
    """An error handler without @context_requires is a standard signature."""

    @pytest.mark.asyncio
    async def test_error_handler_standard_six_params(self) -> None:
        """An error handler without @context_requires is called with 6 parameters,
        without access to context."""
        # Arrange
        bench = TestBench()
        params = _IntegrationParams(name="test")

        #Act - handler without context, 6 parameters
        result = await bench.run(_OnErrorNoCtxAction(), params, rollup=False)

        #Assert - the handler has completed
        assert result.message == "error: test error"


class TestSummaryWithContextRequires:
    """A summary aspect with @context_requires gets a ContextView."""

    @pytest.mark.asyncio
    async def test_summary_reads_hostname(self) -> None:
        """Summary aspect with @context_requires(Ctx.Runtime.hostname) gets
        ContextView and reads the hostname from the context."""
        #Arrange - bench with runtime hostname
        bench = TestBench().with_runtime(hostname="prod-01")
        params = _IntegrationParams(name="test")

        #Act - summary reads hostname via ctx
        result = await bench.run(_SummaryCtxAction(), params, rollup=False)

        #Assert - hostname from the context is included in the result
        assert result.message == "host=prod-01"


class TestBoxContextNotAccessible:
    """ToolsBox does not provide public access to the context."""

    @pytest.mark.asyncio
    async def test_box_has_no_context_property(self) -> None:
        """ToolsBox does not have a public context property and does not have a get_context() method.
        The only legal way to get context data in an aspect is
        via ContextView if @context_requires is present."""
        bench = TestBench()
        params = _BoxCheckParams()

        #Act - Action checks for the presence of box.context
        result = await bench.run(_BoxCheckAction(), params, rollup=False)

        #Assert - box.context is not available
        assert result.has_context is False
        assert result.has_context is False
