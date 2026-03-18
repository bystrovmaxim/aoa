# tests/context/test_environment_info.py
"""
Тесты для класса EnvironmentInfo.

Проверяем:
- Создание с атрибутами
- Доступ через атрибуты и dict-протокол
- Значения по умолчанию
"""

from action_machine.Context.environment_info import EnvironmentInfo


class TestEnvironmentInfo:
    """Тесты для EnvironmentInfo."""

    def test_create_with_attributes(self):
        """Создание EnvironmentInfo с переданными атрибутами."""
        env = EnvironmentInfo(
            hostname="host1",
            service_name="api",
            service_version="1.0",
            environment="prod",
            container_id="c123",
            pod_name="pod1",
            extra={"region": "us-east"},
        )

        assert env.hostname == "host1"
        assert env.service_name == "api"
        assert env.service_version == "1.0"
        assert env.environment == "prod"
        assert env.container_id == "c123"
        assert env.pod_name == "pod1"
        assert env.extra == {"region": "us-east"}

    def test_default_values(self):
        """Проверка значений по умолчанию."""
        env = EnvironmentInfo()

        assert env.hostname is None
        assert env.service_name is None
        assert env.service_version is None
        assert env.environment is None
        assert env.container_id is None
        assert env.pod_name is None
        assert env.extra == {}

    def test_dict_protocol(self):
        """Проверка dict-доступа."""
        env = EnvironmentInfo(hostname="test")
        assert env["hostname"] == "test"
        assert "hostname" in env
        assert env.get("hostname") == "test"