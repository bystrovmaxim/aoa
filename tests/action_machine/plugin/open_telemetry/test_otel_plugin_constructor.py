# tests/action_machine/plugin/open_telemetry/test_otel_plugin_constructor.py
"""Unit tests for OpenTelemetryPlugin constructor validation and provider wiring."""

from unittest.mock import MagicMock

import pytest

from aoa.action_machine.plugin.open_telemetry import OpenTelemetryPlugin


def _mock_tracer_provider() -> MagicMock:
    tp = MagicMock()
    tp.get_tracer.return_value = MagicMock()
    return tp


def _mock_logger_provider() -> MagicMock:
    lp = MagicMock()
    lp.get_logger.return_value = MagicMock()
    return lp


class TestConstructorValidation:
    """Constructor raises ValueError when neither provider is given."""

    def test_no_providers_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            OpenTelemetryPlugin()

    def test_tracer_provider_only_ok(self) -> None:
        plugin = OpenTelemetryPlugin(tracer_provider=_mock_tracer_provider())
        assert plugin._tracer is not None
        assert plugin._otel_logger is None

    def test_logger_provider_only_ok(self) -> None:
        plugin = OpenTelemetryPlugin(logger_provider=_mock_logger_provider())
        assert plugin._tracer is None
        assert plugin._otel_logger is not None

    def test_both_providers_ok(self) -> None:
        plugin = OpenTelemetryPlugin(
            tracer_provider=_mock_tracer_provider(),
            logger_provider=_mock_logger_provider(),
        )
        assert plugin._tracer is not None
        assert plugin._otel_logger is not None


class TestConstructorOptions:
    """Optional parameters are stored correctly."""

    def test_default_max_field_length(self) -> None:
        plugin = OpenTelemetryPlugin(logger_provider=_mock_logger_provider())
        assert plugin._max_field_length == 500

    def test_custom_max_field_length(self) -> None:
        plugin = OpenTelemetryPlugin(
            logger_provider=_mock_logger_provider(),
            max_field_length=100,
        )
        assert plugin._max_field_length == 100

    def test_service_name_passed_to_tracer(self) -> None:
        tp = _mock_tracer_provider()
        OpenTelemetryPlugin(tracer_provider=tp, service_name="my-svc")
        tp.get_tracer.assert_called_once_with("my-svc")

    def test_service_name_passed_to_logger(self) -> None:
        lp = _mock_logger_provider()
        OpenTelemetryPlugin(logger_provider=lp, service_name="my-svc")
        lp.get_logger.assert_called_once_with("my-svc")

    def test_watch_actions_stored(self) -> None:
        class FakeAction:
            pass

        plugin = OpenTelemetryPlugin(
            logger_provider=_mock_logger_provider(),
            watch_actions=frozenset({FakeAction}),
        )
        assert plugin._watch_actions == frozenset({FakeAction})

    def test_watch_events_stored(self) -> None:
        from aoa.action_machine.plugin.core.events import GlobalFinishEvent

        plugin = OpenTelemetryPlugin(
            logger_provider=_mock_logger_provider(),
            watch_events=frozenset({GlobalFinishEvent}),
        )
        assert plugin._watch_events == frozenset({GlobalFinishEvent})
