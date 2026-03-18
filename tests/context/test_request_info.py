# tests/context/test_request_info.py
"""
Тесты для класса RequestInfo.

Проверяем:
- Создание с атрибутами
- Доступ через атрибуты и dict-протокол
- Значения по умолчанию
"""

from datetime import datetime

from action_machine.Context.request_info import RequestInfo


class TestRequestInfo:
    """Тесты для RequestInfo."""

    def test_create_with_attributes(self):
        """Создание RequestInfo с переданными атрибутами."""
        now = datetime.now()
        req = RequestInfo(
            trace_id="trace123",
            request_timestamp=now,
            request_path="/api/test",
            request_method="POST",
            client_ip="192.168.1.1",
            protocol="https",
            user_agent="pytest",
            extra={"key": "value"},
            tags={"env": "test"},
        )

        assert req.trace_id == "trace123"
        assert req.request_timestamp == now
        assert req.request_path == "/api/test"
        assert req.request_method == "POST"
        assert req.client_ip == "192.168.1.1"
        assert req.protocol == "https"
        assert req.user_agent == "pytest"
        assert req.extra == {"key": "value"}
        assert req.tags == {"env": "test"}

    def test_default_values(self):
        """Проверка значений по умолчанию."""
        req = RequestInfo()

        assert req.trace_id is None
        assert req.request_timestamp is None
        assert req.request_path is None
        assert req.request_method is None
        assert req.client_ip is None
        assert req.protocol is None
        assert req.user_agent is None
        assert req.extra == {}
        assert req.tags == {}

    def test_dict_protocol(self):
        """Проверка dict-доступа."""
        req = RequestInfo(trace_id="abc")
        assert req["trace_id"] == "abc"
        assert "trace_id" in req
        assert req.get("trace_id") == "abc"
        assert req.get("missing", "x") == "x"