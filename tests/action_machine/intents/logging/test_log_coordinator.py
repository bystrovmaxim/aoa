# tests/intents/logging/test_log_coordinator.py
"""
Tests for LogCoordinator — the central logging hub.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

LogCoordinator is the sole bus through which all log messages flow. It accepts a
message, substitutes variables from multiple namespaces (var, context,
params, state, scope) via VariableSubstitutor, evaluates ``iif`` constructs, then
fans the result out to every registered logger.

The coordinator invokes ``logger.handle()`` for each logger. ``handle()`` is defined
on BaseLogger and runs a two-phase protocol:
1. Filtering — ``match_filters()`` and ``subscribe()`` rules.
2. Writing — ``write()`` performs actual output only when filtering passes.

RecordingLogger inherits BaseLogger.handle() without overriding it.

═══════════════════════════════════════════════════════════════════════════════
COVERAGE
═══════════════════════════════════════════════════════════════════════════════

Variable substitution:
    - From var: {%var.key}
    - From context: {%context.user.user_id}
    - From params: {%params.amount}
    - From state: {%state.total}
    - From scope: {%scope.action}

``iif`` constructs:
    - Simple conditions embedded in messages.
    - Nested ``iif``.
    - Variables inside ``iif``.

Fan-out:
    - The message reaches every registered logger.
    - Each logger filters independently via BaseLogger.handle().
    - An empty logger list does not raise.

Parameters:
    - ``indent`` is forwarded to loggers.
    - ``scope`` is forwarded to loggers.

Errors:
    - Missing variable → LogTemplateError.
    - Unknown namespace → LogTemplateError.
    - Invalid ``iif`` → LogTemplateError.
    - Leading-underscore names → LogTemplateError.

"""

import logging
from typing import Any

import pytest

from aoa.action_machine.context.context import Context
from aoa.action_machine.exceptions import LogTemplateError
from aoa.action_machine.logging.base_logger import BaseLogger
from aoa.action_machine.logging.channel import Channel, channel_mask_label
from aoa.action_machine.logging.level import Level, level_label
from aoa.action_machine.logging.log_coordinator import LogCoordinator
from aoa.action_machine.logging.log_scope import LogScope
from aoa.action_machine.logging.log_var_payloads import LogChannelPayload, LogLevelPayload
from aoa.action_machine.model.base_params import BaseParams
from aoa.action_machine.model.base_state import BaseState


def _valid_emit_var(**extra: Any) -> dict[str, Any]:
    li = Level.info
    cd = Channel.debug
    return {
        "level": LogLevelPayload(mask=li, name=level_label(li)),
        "channels": LogChannelPayload(mask=cd, names=channel_mask_label(cd)),
        "domain": None,
        "domain_name": None,
        **extra,
    }


class RecordingLogger(BaseLogger):
    """Spy logger: collects ``write`` calls in ``records`` (same contract as ConsoleLogger)."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[dict[str, Any]] = []

    async def write(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        indent: int,
    ) -> None:
        """Append one ``write`` call to ``records``."""
        self.records.append({
            "scope": scope,
            "message": message,
            "var": var.copy(),
            "ctx": ctx,
            "state": state.to_dict(),
            "params": params,
            "indent": indent,
        })


class FailingLogger(BaseLogger):
    """Raises from ``write`` — used to test isolation during fan-out."""

    def __init__(self) -> None:
        super().__init__()
        self.write_calls = 0

    async def write(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        indent: int,
    ) -> None:
        self.write_calls += 1
        raise RuntimeError("intentional sink failure")


@pytest.fixture
def empty_context() -> Context:
    return Context()


@pytest.fixture
def empty_state() -> BaseState:
    return BaseState()


@pytest.fixture
def empty_params() -> BaseParams:
    return BaseParams()


@pytest.fixture
def simple_scope() -> LogScope:
    return LogScope(action="TestAction")


@pytest.fixture
def detailed_scope() -> LogScope:
    return LogScope(action="TestAction", aspect="validate")


# ======================================================================
# TESTS: variable substitution from multiple sources
# ======================================================================


class TestVariableSubstitution:
    """LogCoordinator substitutes variables from var, context, params, state, scope."""

    @pytest.mark.anyio
    async def test_substitutes_var(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        {%var.count} resolves from the ``var`` dict.
        """
        # Arrange
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        var = _valid_emit_var(count=42)

        # Act
        await coordinator.emit(
            message="Count is {%var.count}",
            var=var,
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Count is 42"

    @pytest.mark.anyio
    async def test_substitutes_context(
        self,
        simple_scope: LogScope,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        {%context.user.user_id} resolves via Context.
        """
        # Arrange
        from aoa.action_machine.context.user_info import UserInfo
        ctx = Context(user=UserInfo(user_id="agent_007"))
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="User: {%context.user.user_id}",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=ctx,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "User: agent_007"

    @pytest.mark.anyio
    async def test_substitutes_params(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
    ) -> None:
        """
        {%params.amount} resolves from the Pydantic params model.
        """
        # Arrange
        from pydantic import Field
        class TestParams(BaseParams):
            amount: float = Field(default=999.99, description="Amount")

        params = TestParams(amount=999.99)
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="Amount: {%params.amount}",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Amount: 999.99"

    @pytest.mark.anyio
    async def test_substitutes_state(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_params: BaseParams,
    ) -> None:
        """
        {%state.total} resolves from BaseState.
        """
        # Arrange
        state = BaseState(total=1500.0)
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="Total: {%state.total}",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Total: 1500.0"

    @pytest.mark.anyio
    async def test_substitutes_scope(
        self,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        {%scope.action} resolves from LogScope.
        """
        # Arrange
        scope = LogScope(action="ProcessOrder", aspect="validate")
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="Action: {%scope.action}",
            var=_valid_emit_var(),
            scope=scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Action: ProcessOrder"


# ======================================================================
# TESTS: ``iif`` constructs
# ======================================================================


class TestIifConstructs:
    """LogCoordinator evaluates ``{iif(...)}`` constructs."""

    @pytest.mark.anyio
    async def test_simple_iif(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        ``{iif(condition; branch_true; branch_false)}`` is evaluated and inlined.
        """
        # Arrange
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        var = _valid_emit_var(amount=1500.0)

        # Act — ``iif`` referencing {%var.amount}
        await coordinator.emit(
            message="Risk: {iif({%var.amount} > 1000; 'HIGH'; 'LOW')}",
            var=var,
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Risk: HIGH"

    @pytest.mark.anyio
    async def test_nested_iif(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Nested ``iif`` forms evaluate correctly.
        """
        # Arrange
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        var = _valid_emit_var(amount=1500000.0)

        # Act
        await coordinator.emit(
            message="Level: {iif({%var.amount} > 1000000; 'CRITICAL'; iif({%var.amount} > 100000; 'HIGH'; 'LOW'))}",
            var=var,
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Level: CRITICAL"

    @pytest.mark.anyio
    async def test_iif_with_state(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_params: BaseParams,
    ) -> None:
        """
        ``iif`` may reference ``state`` variables.
        """
        # Arrange
        state = BaseState(processed=True)
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="Status: {iif({%state.processed} == True; 'DONE'; 'PENDING')}",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Status: DONE"


# ======================================================================
# TESTS: fan-out to loggers
# ======================================================================


class TestBroadcast:
    """Message is delivered to every registered logger."""

    @pytest.mark.anyio
    async def test_broadcast_to_all_loggers(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Each logger receives the message after its own filtering.
        """
        # Arrange — two loggers with no filters
        logger1 = RecordingLogger()
        logger2 = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger1, logger2])

        # Act
        await coordinator.emit(
            message="Broadcast",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert — both captured the message
        assert len(logger1.records) == 1
        assert len(logger2.records) == 1
        assert logger1.records[0]["message"] == "Broadcast"
        assert logger2.records[0]["message"] == "Broadcast"

    @pytest.mark.anyio
    async def test_respects_logger_filters(
        self,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Loggers filter independently; the second logger's subscriptions do not
        match the channel carried in ``var`` (debug vs business).
        """
        all_logger = RecordingLogger()
        filtered_logger = RecordingLogger()
        filtered_logger.subscribe("only_business", channels=Channel.business)
        coordinator = LogCoordinator(loggers=[all_logger, filtered_logger])
        scope = LogScope(action="OrderAction")

        await coordinator.emit(
            message="Order created",
            var=_valid_emit_var(),
            scope=scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        assert len(all_logger.records) == 1
        assert len(filtered_logger.records) == 0

    @pytest.mark.anyio
    async def test_add_logger(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        A logger can be attached after coordinator construction.
        """
        # Arrange
        coordinator = LogCoordinator()
        logger = RecordingLogger()

        # Act
        coordinator.add_logger(logger)
        await coordinator.emit(
            message="After add",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_emit_without_loggers(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Emitting with zero loggers does not raise.
        """
        # Arrange
        coordinator = LogCoordinator()

        # Act — must complete without exceptions
        await coordinator.emit(
            message="No loggers",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )


# ======================================================================
# TESTS: isolation when logger.handle fails (B-2 / best-effort logging)
# ======================================================================


_COORDINATOR_FAILURE_LOGGER = "aoa.action_machine.logging.log_coordinator"


class TestLoggerHandleFailureIsolation:
    """A failing BaseLogger must not break ``emit`` or block sibling sinks."""

    @pytest.mark.anyio
    async def test_second_logger_receives_message_when_first_raises(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        failing = FailingLogger()
        recording = RecordingLogger()
        coordinator = LogCoordinator(loggers=[failing, recording])

        await coordinator.emit(
            message="Fan-out",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        assert failing.write_calls == 1
        assert len(recording.records) == 1
        assert recording.records[0]["message"] == "Fan-out"

    @pytest.mark.anyio
    async def test_emit_completes_when_all_loggers_fail(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        a = FailingLogger()
        b = FailingLogger()
        coordinator = LogCoordinator(loggers=[a, b])

        await coordinator.emit(
            message="All bad",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        assert a.write_calls == 1
        assert b.write_calls == 1

    @pytest.mark.anyio
    async def test_failed_logger_emits_stdlib_error_record(
        self,
        caplog: pytest.LogCaptureFixture,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """With no sibling sink, failures are reported through stdlib logging."""
        coordinator = LogCoordinator(loggers=[FailingLogger()])
        with caplog.at_level(logging.ERROR, logger=_COORDINATOR_FAILURE_LOGGER):
            await coordinator.emit(
                message="Sink down",
                var=_valid_emit_var(),
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )

        assert any(
            "LogCoordinator" in r.getMessage() and "raised during emit" in r.getMessage()
            for r in caplog.records
        )


# ======================================================================
# TESTS: forwarding parameters to loggers
# ======================================================================


class TestParameterPassing:
    """LogCoordinator forwards logger parameters unchanged."""

    @pytest.mark.anyio
    async def test_passes_indent(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        ``indent`` is forwarded to each sink untouched.
        """
        # Arrange
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="Indented",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=5,
        )

        # Assert
        assert logger.records[0]["indent"] == 5

    @pytest.mark.anyio
    async def test_passes_scope(
        self,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        ``scope`` is forwarded to sinks.
        """
        # Arrange
        scope = LogScope(action="MyAction", aspect="test")
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="Test",
            var=_valid_emit_var(),
            scope=scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["scope"] is scope


# ======================================================================
# TESTS: nested structures
# ======================================================================


class TestNestedStructures:
    """Substitution for nested payloads (dicts inside state, var, etc.)."""

    @pytest.mark.anyio
    async def test_nested_state(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_params: BaseParams,
    ) -> None:
        """
        Dot paths into ``state`` work: {%state.order.id}.
        """
        # Arrange
        state = BaseState(order={"id": 42})
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="Order ID: {%state.order.id}",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Order ID: 42"

    @pytest.mark.anyio
    async def test_nested_var(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Dot paths into ``var`` work: {%var.data.value}.
        """
        # Arrange
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        var = _valid_emit_var(data={"value": "deep"})

        # Act
        await coordinator.emit(
            message="Value: {%var.data.value}",
            var=var,
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Value: deep"

    @pytest.mark.anyio
    async def test_substitutes_level_name_and_channel_names(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        await coordinator.emit(
            message="{%var.level.name}|{%var.channels.names}",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )
        assert logger.records[0]["message"] == "INFO|debug"


# ======================================================================
# TESTS: error handling
# ======================================================================


class TestErrorHandling:
    """LogCoordinator raises LogTemplateError for template errors."""

    @pytest.mark.anyio
    async def test_emit_requires_level_and_channels(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        coordinator = LogCoordinator(loggers=[])
        with pytest.raises(ValueError, match="var must contain"):
            await coordinator.emit(
                message="x",
                var={"channels": LogChannelPayload(
                    mask=Channel.debug, names=channel_mask_label(Channel.debug),
                )},
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_rejects_raw_level_not_payload(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        coordinator = LogCoordinator(loggers=[])
        bad = {**_valid_emit_var(), "level": Level.info}
        with pytest.raises(TypeError, match="LogLevelPayload"):
            await coordinator.emit(
                message="x",
                var=bad,
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_missing_variable_raises(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Referencing a missing variable → LogTemplateError.
        """
        # Arrange
        coordinator = LogCoordinator(loggers=[])

        # Act & Assert
        with pytest.raises(LogTemplateError, match="not found"):
            await coordinator.emit(
                message="Missing: {%var.nonexistent}",
                var=_valid_emit_var(),
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_unknown_namespace_raises(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Unknown template namespace → LogTemplateError.
        """
        # Arrange
        coordinator = LogCoordinator(loggers=[])

        # Act & Assert
        with pytest.raises(LogTemplateError, match="Unknown namespace"):
            await coordinator.emit(
                message="Value: {%unknown.field}",
                var=_valid_emit_var(),
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_underscore_name_raises(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Leading-underscore names remain forbidden → LogTemplateError.
        """
        # Arrange
        coordinator = LogCoordinator(loggers=[])
        var = {**_valid_emit_var(), "_secret": "value"}

        # Act & Assert
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            await coordinator.emit(
                message="Secret: {%var._secret}",
                var=var,
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_missing_variable_in_iif_raises(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Missing variable inside ``iif`` → LogTemplateError.
        """
        # Arrange
        coordinator = LogCoordinator(loggers=[])

        # Act & Assert
        with pytest.raises(LogTemplateError, match="not found"):
            await coordinator.emit(
                message="Result: {iif({%var.missing} > 10; 'yes'; 'no')}",
                var=_valid_emit_var(),
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_invalid_iif_syntax_raises(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Invalid ``iif`` arity → LogTemplateError.
        """
        # Arrange
        coordinator = LogCoordinator(loggers=[])

        # Act & Assert
        with pytest.raises(LogTemplateError, match="iif expects 3 arguments"):
            await coordinator.emit(
                message="Bad: {iif(1 > 0; 'only_two_args')}",
                var=_valid_emit_var(),
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )
