# tests/otel/test_otel_emit_log.py
"""Unit tests for OpenTelemetryPlugin._emit_log — OTel log record emission."""

from unittest.mock import MagicMock

from aoa.action_machine.context.context import Context
from aoa.action_machine.context.request_info import RequestInfo
from aoa.action_machine.context.user_info import UserInfo
from aoa.action_machine.plugin.core.events import GlobalStartEvent
from aoa.otel import OpenTelemetryPlugin

from .support import PingAction


def _make_plugin_with_mock_logger() -> tuple[OpenTelemetryPlugin, MagicMock]:
    mock_logger = MagicMock()
    lp = MagicMock()
    lp.get_logger.return_value = mock_logger
    plugin = OpenTelemetryPlugin(logger_provider=lp)
    return plugin, mock_logger


def _make_event(trace_id: str | None = None) -> GlobalStartEvent:
    ctx = Context(
        user=UserInfo(user_id="u1", roles=()),
        request=RequestInfo(trace_id=trace_id),
    )
    return GlobalStartEvent(
        action_class=PingAction,
        action_name="PingAction",
        nest_level=1,
        context=ctx,
        params=PingAction.Params(),
    )


class TestEmitLogNoOp:
    """_emit_log is a no-op when logger_provider was not provided."""

    def test_tracer_only_plugin_does_not_emit(self) -> None:
        tp = MagicMock()
        mock_tracer = MagicMock()
        tp.get_tracer.return_value = mock_tracer
        plugin = OpenTelemetryPlugin(tracer_provider=tp)

        # Should not raise and _otel_logger is None
        plugin._emit_log(body="test", attributes={})
        assert plugin._otel_logger is None


class TestEmitLogCallsEmit:
    """_emit_log calls otel_logger.emit with a LogRecord."""

    def test_emit_called_on_logger(self) -> None:
        plugin, mock_logger = _make_plugin_with_mock_logger()
        plugin._emit_log(body="aoa.action.start", attributes={"aoa.action": "Foo"})
        assert mock_logger.emit.called

    def test_emit_called_once(self) -> None:
        plugin, mock_logger = _make_plugin_with_mock_logger()
        plugin._emit_log(body="aoa.action.start", attributes={})
        assert mock_logger.emit.call_count == 1

    def test_log_record_body_matches(self) -> None:
        from opentelemetry._logs import LogRecord

        plugin, mock_logger = _make_plugin_with_mock_logger()
        plugin._emit_log(body="aoa.aspect.regular.after", attributes={"k": "v"})

        args, _ = mock_logger.emit.call_args
        record = args[0]
        assert isinstance(record, LogRecord)
        assert record.body == "aoa.aspect.regular.after"

    def test_attributes_passed_to_record(self) -> None:

        plugin, mock_logger = _make_plugin_with_mock_logger()
        plugin._emit_log(body="x", attributes={"aoa.action": "MyAction", "aoa.duration_ms": 42.0})

        args, _ = mock_logger.emit.call_args
        record = args[0]
        assert record.attributes["aoa.action"] == "MyAction"
        assert record.attributes["aoa.duration_ms"] == 42.0


class TestEmitLogTraceId:
    """aoa.trace_id is added when context.request.trace_id is set."""

    def test_trace_id_added_when_set(self) -> None:

        plugin, mock_logger = _make_plugin_with_mock_logger()
        event = _make_event(trace_id="req-abc-123")
        plugin._emit_log(body="aoa.action.start", attributes={}, event=event)

        args, _ = mock_logger.emit.call_args
        record = args[0]
        assert record.attributes.get("aoa.trace_id") == "req-abc-123"

    def test_trace_id_not_added_when_none(self) -> None:

        plugin, mock_logger = _make_plugin_with_mock_logger()
        event = _make_event(trace_id=None)
        plugin._emit_log(body="aoa.action.start", attributes={}, event=event)

        args, _ = mock_logger.emit.call_args
        record = args[0]
        assert "aoa.trace_id" not in record.attributes

    def test_no_event_no_trace_id(self) -> None:

        plugin, mock_logger = _make_plugin_with_mock_logger()
        plugin._emit_log(body="aoa.action.start", attributes={}, event=None)

        args, _ = mock_logger.emit.call_args
        record = args[0]
        assert "aoa.trace_id" not in record.attributes
