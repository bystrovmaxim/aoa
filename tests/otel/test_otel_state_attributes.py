# tests/action_machine/plugin/open_telemetry/test_otel_state_attributes.py
"""Unit tests for OpenTelemetryPlugin._state_attributes — opaque field exclusion."""

from unittest.mock import MagicMock

from aoa.action_machine.plugin.open_telemetry import OpenTelemetryPlugin


def _plugin() -> OpenTelemetryPlugin:
    lp = MagicMock()
    lp.get_logger.return_value = MagicMock()
    return OpenTelemetryPlugin(logger_provider=lp)


class TestStateAttributesEmpty:
    """Empty or None data produces empty attribute dict."""

    def test_none_data_returns_empty(self) -> None:
        assert _plugin()._state_attributes(None) == {}

    def test_empty_dict_returns_empty(self) -> None:
        assert _plugin()._state_attributes({}) == {}


class TestStateAttributesInclusion:
    """Non-opaque fields are included as aoa.state.<key>."""

    def test_single_field_included(self) -> None:
        result = _plugin()._state_attributes({"order_id": "ORD-001"})
        assert "aoa.state.order_id" in result
        assert result["aoa.state.order_id"] == "ORD-001"

    def test_multiple_fields_included(self) -> None:
        result = _plugin()._state_attributes({"a": 1, "b": "hello"})
        assert "aoa.state.a" in result
        assert "aoa.state.b" in result

    def test_primitive_types_serialized_correctly(self) -> None:
        result = _plugin()._state_attributes({"n": 42, "f": 1.5, "flag": True})
        assert result["aoa.state.n"] == 42
        assert result["aoa.state.f"] == 1.5
        assert result["aoa.state.flag"] is True


class TestStateAttributesOpaqueExclusion:
    """Opaque fields are excluded; non-opaque fields remain."""

    def test_opaque_field_excluded(self) -> None:
        data = {"order_id": "ORD-001", "rich_obj": object()}
        result = _plugin()._state_attributes(data, opaque_fields=frozenset({"rich_obj"}))
        assert "aoa.state.rich_obj" not in result
        assert "aoa.state.order_id" in result

    def test_non_opaque_field_included_when_others_excluded(self) -> None:
        data = {"keep": "yes", "drop": "no"}
        result = _plugin()._state_attributes(data, opaque_fields=frozenset({"drop"}))
        assert "aoa.state.keep" in result
        assert "aoa.state.drop" not in result

    def test_all_fields_opaque_returns_empty(self) -> None:
        data = {"a": 1, "b": 2}
        result = _plugin()._state_attributes(data, opaque_fields=frozenset({"a", "b"}))
        assert result == {}

    def test_empty_opaque_set_includes_all(self) -> None:
        data = {"x": 10, "y": 20}
        result = _plugin()._state_attributes(data, opaque_fields=frozenset())
        assert "aoa.state.x" in result
        assert "aoa.state.y" in result

    def test_default_opaque_fields_includes_all(self) -> None:
        data = {"x": 10}
        result = _plugin()._state_attributes(data)
        assert "aoa.state.x" in result
