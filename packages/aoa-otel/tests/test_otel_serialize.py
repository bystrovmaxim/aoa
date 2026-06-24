# tests/otel/test_otel_serialize.py
"""Unit tests for _serialize_value — OTel-safe serialization of state fields."""

import json

from pydantic import BaseModel

from aoa.otel.plugin.open_telemetry_plugin import _serialize_value

_MAX = 500


class TestPrimitivePassthrough:
    """Primitive values are returned unchanged (no serialization)."""

    def test_str_passthrough(self) -> None:
        assert _serialize_value("hello", _MAX) == "hello"

    def test_int_passthrough(self) -> None:
        assert _serialize_value(42, _MAX) == 42

    def test_float_passthrough(self) -> None:
        assert _serialize_value(3.14, _MAX) == 3.14

    def test_bool_true_passthrough(self) -> None:
        assert _serialize_value(True, _MAX) is True

    def test_bool_false_passthrough(self) -> None:
        assert _serialize_value(False, _MAX) is False

    def test_none_passthrough(self) -> None:
        assert _serialize_value(None, _MAX) is None


class TestPydanticModelDump:
    """Pydantic models are serialized via model_dump() → json.dumps()."""

    def test_simple_pydantic_model(self) -> None:
        class Order(BaseModel):
            id: int
            status: str

        result = _serialize_value(Order(id=1, status="new"), _MAX)
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed == {"id": 1, "status": "new"}

    def test_nested_pydantic_model(self) -> None:
        class Address(BaseModel):
            city: str

        class User(BaseModel):
            name: str
            address: Address

        result = _serialize_value(User(name="Alice", address=Address(city="Moscow")), _MAX)
        parsed = json.loads(result)
        assert parsed["name"] == "Alice"
        assert parsed["address"]["city"] == "Moscow"


class TestComplexObjectFallback:
    """Non-pydantic objects fall back to json.dumps(default=repr)."""

    def test_dict_is_json_serialized(self) -> None:
        result = _serialize_value({"a": 1, "b": [2, 3]}, _MAX)
        assert isinstance(result, str)
        assert json.loads(result) == {"a": 1, "b": [2, 3]}

    def test_list_is_json_serialized(self) -> None:
        result = _serialize_value([1, 2, 3], _MAX)
        assert isinstance(result, str)
        assert json.loads(result) == [1, 2, 3]

    def test_unserializable_object_falls_back_to_repr(self) -> None:
        class Unserializable:
            def __repr__(self) -> str:
                return "<Unserializable>"

            def __json__(self) -> None:
                raise TypeError("not serializable")

        result = _serialize_value(Unserializable(), _MAX)
        assert isinstance(result, str)
        assert "Unserializable" in result


class TestTruncation:
    """Serialized text exceeding max_length is truncated with ...[truncated]."""

    def test_truncation_applied(self) -> None:
        big_dict = {"key": "x" * 600}
        result = _serialize_value(big_dict, 100)
        assert isinstance(result, str)
        assert result.endswith("...[truncated]")
        assert len(result) == 100 + len("...[truncated]")

    def test_no_truncation_when_within_limit(self) -> None:
        small = {"k": "v"}
        result = _serialize_value(small, _MAX)
        assert isinstance(result, str)
        assert "truncated" not in result

    def test_truncation_at_exact_boundary(self) -> None:
        text = "x" * 500
        result = _serialize_value({"k": text}, 500)
        assert isinstance(result, str)
        # JSON of {"k": "x"*500} = 508 chars → truncated
        assert result.endswith("...[truncated]")
