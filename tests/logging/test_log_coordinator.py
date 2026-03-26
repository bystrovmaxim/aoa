# tests/logging/test_log_coordinator.py
"""
Tests for LogCoordinator – the logging coordinator.

Checks:
- Variable substitution from different sources (var, context, params, state, scope)
- iif construct handling
- Broadcast to multiple loggers
- Filtering through loggers
- Error handling (non-existent variables, unknown namespace)
"""

import pytest

from action_machine.core.base_state import BaseState
from action_machine.core.exceptions import LogTemplateError
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.log_scope import LogScope
from tests.conftest import ParamsTest, RecordingLogger, make_context


class TestLogCoordinator:
    """Tests for the logging coordinator."""

    # ------------------------------------------------------------------
    # TESTS: Variable substitution from different sources
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_emit_substitutes_var(self, recording_logger, scope, context_fixture, params):
        """emit substitutes variables from var."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        await coordinator.emit(
            message="Count is {%var.count}",
            var={"count": 42},
            scope=scope,
            ctx=context_fixture,
            state=BaseState(),
            params=params,
            indent=0,
        )
        assert recording_logger.records[0]["message"] == "Count is 42"

    @pytest.mark.anyio
    async def test_emit_substitutes_context(self, recording_logger, scope, params):
        """emit substitutes variables from context via resolve."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        ctx = make_context(user_id="agent_007")
        await coordinator.emit(
            message="User: {%context.user.user_id}",
            var={},
            scope=scope,
            ctx=ctx,
            state=BaseState(),
            params=params,
            indent=0,
        )
        assert recording_logger.records[0]["message"] == "User: agent_007"

    @pytest.mark.anyio
    async def test_emit_substitutes_params(self, recording_logger, scope, context_fixture):
        """emit substitutes variables from params via resolve."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        params = ParamsTest(amount=999.99)
        await coordinator.emit(
            message="Amount: {%params.amount}",
            var={},
            scope=scope,
            ctx=context_fixture,
            state=BaseState(),
            params=params,
            indent=0,
        )
        assert recording_logger.records[0]["message"] == "Amount: 999.99"

    @pytest.mark.anyio
    async def test_emit_substitutes_state(self, recording_logger, scope, context_fixture, params):
        """emit substitutes variables from state."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        await coordinator.emit(
            message="Total: {%state.total}",
            var={},
            scope=scope,
            ctx=context_fixture,
            state=BaseState({"total": 1500.0}),
            params=params,
            indent=0,
        )
        assert recording_logger.records[0]["message"] == "Total: 1500.0"

    @pytest.mark.anyio
    async def test_emit_substitutes_scope(self, recording_logger, context_fixture, params):
        """emit substitutes variables from scope."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        scope = LogScope(action="ProcessOrder", aspect="validate")
        await coordinator.emit(
            message="Action: {%scope.action}",
            var={},
            scope=scope,
            ctx=context_fixture,
            state=BaseState(),
            params=params,
            indent=0,
        )
        assert recording_logger.records[0]["message"] == "Action: ProcessOrder"

    # ------------------------------------------------------------------
    # TESTS: iif constructs
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_emit_with_iif_simple(self, recording_logger, scope, context_fixture):
        """emit handles simple iif with unified {%...} syntax."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        params = ParamsTest(amount=1500.0)
        await coordinator.emit(
            message="Risk: {iif({%params.amount} > 1000; 'HIGH'; 'LOW')}",
            var={},
            scope=scope,
            ctx=context_fixture,
            state=BaseState(),
            params=params,
            indent=0,
        )
        assert recording_logger.records[0]["message"] == "Risk: HIGH"

    @pytest.mark.anyio
    async def test_emit_with_iif_nested(self, recording_logger, scope, context_fixture):
        """emit handles nested iif with unified syntax."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        params = ParamsTest(amount=1500000.0)
        await coordinator.emit(
            message="Level: {iif({%params.amount} > 1000000; 'CRITICAL'; iif({%params.amount} > 100000; 'HIGH'; 'LOW'))}",
            var={},
            scope=scope,
            ctx=context_fixture,
            state=BaseState(),
            params=params,
            indent=0,
        )
        assert recording_logger.records[0]["message"] == "Level: CRITICAL"

    @pytest.mark.anyio
    async def test_emit_with_iif_using_var(self, recording_logger, scope, context_fixture, params):
        """iif uses variables from var."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        await coordinator.emit(
            message="Result: {iif({%var.success} == True; 'OK'; 'FAIL')}",
            var={"success": True},
            scope=scope,
            ctx=context_fixture,
            state=BaseState(),
            params=params,
            indent=0,
        )
        assert recording_logger.records[0]["message"] == "Result: OK"

    @pytest.mark.anyio
    async def test_emit_with_iif_using_state(self, recording_logger, scope, context_fixture, params):
        """iif uses variables from state."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        await coordinator.emit(
            message="Status: {iif({%state.processed} == True; 'DONE'; 'PENDING')}",
            var={},
            scope=scope,
            ctx=context_fixture,
            state=BaseState({"processed": True}),
            params=params,
            indent=0,
        )
        assert recording_logger.records[0]["message"] == "Status: DONE"

    # ------------------------------------------------------------------
    # TESTS: Broadcast to multiple loggers
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_emit_broadcasts_to_all_loggers(self, scope, context_fixture, params):
        """emit broadcasts the message to all registered loggers."""
        logger1 = RecordingLogger()
        logger2 = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger1, logger2])
        await coordinator.emit(
            message="Broadcast",
            var={},
            scope=scope,
            ctx=context_fixture,
            state=BaseState(),
            params=params,
            indent=0,
        )
        assert len(logger1.records) == 1
        assert len(logger2.records) == 1
        assert logger1.records[0]["message"] == "Broadcast"
        assert logger2.records[0]["message"] == "Broadcast"

    @pytest.mark.anyio
    async def test_emit_respects_logger_filters(self, scope, context_fixture, params):
        """emit calls all loggers, but each filters independently."""
        logger_all = RecordingLogger()
        logger_filtered = RecordingLogger(filters=[r"PaymentAction"])
        coordinator = LogCoordinator(loggers=[logger_all, logger_filtered])
        scope = LogScope(action="OrderAction")  # not PaymentAction
        await coordinator.emit(
            message="Order created",
            var={},
            scope=scope,
            ctx=context_fixture,
            state=BaseState(),
            params=params,
            indent=0,
        )
        assert len(logger_all.records) == 1
        assert len(logger_filtered.records) == 0

    @pytest.mark.anyio
    async def test_add_logger(self, scope, context_fixture, params):
        """add_logger adds a logger to the coordinator."""
        coordinator = LogCoordinator()
        logger = RecordingLogger()
        coordinator.add_logger(logger)
        await coordinator.emit(
            message="After add",
            var={},
            scope=scope,
            ctx=context_fixture,
            state=BaseState(),
            params=params,
            indent=0,
        )
        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_emit_without_loggers_does_nothing(self, scope, context_fixture, params):
        """emit without loggers does nothing (no error)."""
        coordinator = LogCoordinator()
        await coordinator.emit(
            message="No loggers",
            var={},
            scope=scope,
            ctx=context_fixture,
            state=BaseState(),
            params=params,
            indent=0,
        )
        # no assertion, just shouldn't crash

    # ------------------------------------------------------------------
    # TESTS: Parameter passing
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_emit_passes_indent_to_loggers(self, recording_logger, scope, context_fixture, params):
        """emit passes indent to each logger."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        await coordinator.emit(
            message="Indented",
            var={},
            scope=scope,
            ctx=context_fixture,
            state=BaseState(),
            params=params,
            indent=5,
        )
        assert recording_logger.records[0]["indent"] == 5

    @pytest.mark.anyio
    async def test_emit_passes_scope_to_loggers(self, recording_logger, context_fixture, params):
        """emit passes scope to each logger."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        test_scope = LogScope(action="TestAction", aspect="test")
        await coordinator.emit(
            message="Test",
            var={},
            scope=test_scope,
            ctx=context_fixture,
            state=BaseState(),
            params=params,
            indent=0,
        )
        assert recording_logger.records[0]["scope"] is test_scope

    # ------------------------------------------------------------------
    # TESTS: Nested structures
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_emit_nested_state_dict(self, recording_logger, scope, context_fixture, params):
        """emit substitutes nested values from state."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        await coordinator.emit(
            message="Nested: {%state.order.id}",
            var={},
            scope=scope,
            ctx=context_fixture,
            state=BaseState({"order": {"id": 42}}),
            params=params,
            indent=0,
        )
        assert recording_logger.records[0]["message"] == "Nested: 42"

    @pytest.mark.anyio
    async def test_emit_nested_var_dict(self, recording_logger, scope, context_fixture, params):
        """emit substitutes nested values from var."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        await coordinator.emit(
            message="Var nested: {%var.data.value}",
            var={"data": {"value": "deep"}},
            scope=scope,
            ctx=context_fixture,
            state=BaseState(),
            params=params,
            indent=0,
        )
        assert recording_logger.records[0]["message"] == "Var nested: deep"

    # ------------------------------------------------------------------
    # TESTS: Error handling
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_emit_missing_variable_raises(self, scope, context_fixture, params):
        """Access to a non-existent variable raises LogTemplateError."""
        coordinator = LogCoordinator(loggers=[RecordingLogger()])
        with pytest.raises(LogTemplateError, match="not found"):
            await coordinator.emit(
                message="Missing: {%var.nonexistent}",
                var={},
                scope=scope,
                ctx=context_fixture,
                state=BaseState(),
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_missing_variable_in_iif_raises(self, scope, context_fixture, params):
        """Access to a non-existent variable inside iif raises LogTemplateError."""
        coordinator = LogCoordinator(loggers=[RecordingLogger()])
        with pytest.raises(LogTemplateError, match="not found"):
            await coordinator.emit(
                message="Result: {iif({%var.missing} > 10; 'yes'; 'no')}",
                var={},
                scope=scope,
                ctx=context_fixture,
                state=BaseState(),
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_unknown_namespace_raises(self, scope, context_fixture, params):
        """Unknown namespace in template raises LogTemplateError."""
        coordinator = LogCoordinator(loggers=[RecordingLogger()])
        with pytest.raises(LogTemplateError, match="Unknown namespace"):
            await coordinator.emit(
                message="Value: {%unknown.field}",
                var={},
                scope=scope,
                ctx=context_fixture,
                state=BaseState(),
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_underscore_name_raises(self, scope, context_fixture, params):
        """Access to a name starting with underscore raises LogTemplateError."""
        coordinator = LogCoordinator(loggers=[RecordingLogger()])
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            await coordinator.emit(
                message="Secret: {%var._secret}",
                var={"_secret": "value"},
                scope=scope,
                ctx=context_fixture,
                state=BaseState(),
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_invalid_iif_syntax_raises(self, scope, context_fixture, params):
        """Invalid iif syntax (not 3 args) raises LogTemplateError."""
        coordinator = LogCoordinator(loggers=[RecordingLogger()])
        with pytest.raises(LogTemplateError, match="iif expects 3 arguments"):
            await coordinator.emit(
                message="Bad: {iif(1 > 0; 'only_two_args')}",
                var={},
                scope=scope,
                ctx=context_fixture,
                state=BaseState(),
                params=params,
                indent=0,
            )