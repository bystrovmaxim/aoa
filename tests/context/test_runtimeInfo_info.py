# tests/context/test_runtimeInfo_info.py
"""
Тесты для класса RuntimeInfo.

Проверяем:
- Создание с атрибутами
- Доступ через атрибуты и dict-протокол
- Значения по умолчанию
"""

from action_machine.Context.runtime_info import RuntimeInfo


class TestRuntimeInfoInfo:
    """Тесты для RuntimeInfo."""

    def test_create_with_attributes(self):
        """Создание RuntimeInfo с переданными атрибутами."""
        env = RuntimeInfo(
            hostname="host1",
            service_name="api",
            service_version="1.0",
            container_id="c123",
            pod_name="pod1",
            extra={"region": "us-east"},
        )

        assert env.hostname == "host1"
        assert env.service_name == "api"
        assert env.service_version == "1.0"
        assert env.container_id == "c123"
        assert env.pod_name == "pod1"
        assert env.extra == {"region": "us-east"}

    def test_default_values(self):
        """Проверка значений по умолчанию."""
        env = RuntimeInfo()

        assert env.hostname is None
        assert env.service_name is None
        assert env.service_version is None
        assert env.container_id is None
        assert env.pod_name is None
        assert env.extra == {}

    def test_dict_protocol(self):
        """Проверка dict-доступа."""
        env = RuntimeInfo(hostname="test")
        assert env["hostname"] == "test"
        assert "hostname" in env
        assert env.get("hostname") == "test"