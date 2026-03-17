"""
Интеграционные тесты для системы аутентификации.

Проверяем работу AuthCoordinator с реальными (но простыми) реализациями
компонентов, а не с моками.
"""

import pytest

from action_machine.Auth.AuthCoordinator import auth_coordinator
from action_machine.Context.Context import context
from action_machine.Context.EnvironmentInfo import environment_info
from action_machine.Context.RequestInfo import request_info
from action_machine.Context.UserInfo import user_info


class TestAuthIntegration:
    """Интеграционные тесты для Auth."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Простые реализации
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_auth_with_simple_components(self):
        """Тест с простыми реализациями компонентов."""

        class SimpleExtractor:
            """Простой экстрактор, достающий токен из запроса."""

            async def extract(self, request_data):
                return {"user": request_data.get("username"), "token": request_data.get("token")}

        class SimpleAuthenticator:
            """Простой аутентификатор, проверяющий токен."""

            async def authenticate(self, credentials):
                if credentials.get("token") == "abc123":
                    return user_info(user_id=credentials.get("user", "unknown"), roles=["user"])
                return None

        class SimpleAssembler:
            """Простой сборщик метаданных."""

            async def assemble(self, request_data):
                return {
                    "trace_id": request_data.get("trace_id", "unknown"),
                    "request_path": "/api/test",
                    "client_ip": request_data.get("ip", "0.0.0.0"),
                }

        coordinator = auth_coordinator(SimpleExtractor(), SimpleAuthenticator(), SimpleAssembler())

        # Успешная аутентификация
        result = await coordinator.process(
            {"username": "john", "token": "abc123", "trace_id": "trace-xyz", "ip": "192.168.1.1"}
        )

        assert result is not None
        assert result.user.user_id == "john"
        assert result.user.roles == ["user"]
        assert result.request.trace_id == "trace-xyz"
        assert result.request.client_ip == "192.168.1.1"

        # Неуспешная аутентификация
        result2 = await coordinator.process({"username": "john", "token": "wrong-token"})

        assert result2 is None

    @pytest.mark.anyio
    async def test_auth_with_empty_extractor(self):
        """Экстрактор может вернуть пустой словарь."""

        class EmptyExtractor:
            async def extract(self, request_data):
                return {}  # пусто

        class Authenticator:
            async def authenticate(self, credentials):
                # Этот метод не должен быть вызван
                pytest.fail("Authenticator не должен вызываться при пустых credentials")

        class Assembler:
            async def assemble(self, request_data):
                pytest.fail("Assembler не должен вызываться при пустых credentials")

        coordinator = auth_coordinator(EmptyExtractor(), Authenticator(), Assembler())

        result = await coordinator.process({"some": "data"})
        assert result is None

    @pytest.mark.anyio
    async def test_auth_with_authenticator_returning_none(self):
        """Аутентификатор может вернуть None."""

        class Extractor:
            async def extract(self, request_data):
                return {"token": "valid"}

        class FailingAuthenticator:
            async def authenticate(self, credentials):
                return None  # аутентификация не удалась

        class Assembler:
            async def assemble(self, request_data):
                pytest.fail("Assembler не должен вызываться при неудачной аутентификации")

        coordinator = auth_coordinator(Extractor(), FailingAuthenticator(), Assembler())

        result = await coordinator.process({})
        assert result is None

    # ------------------------------------------------------------------
    # ТЕСТЫ: Проверка структуры Context
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_auth_returns_proper_context_structure(self):
        """Проверка, что возвращается правильно структурированный Context."""

        class TestExtractor:
            async def extract(self, request_data):
                return {"api_key": "secret"}

        class TestAuthenticator:
            async def authenticate(self, credentials):
                if credentials.get("api_key") == "secret":
                    return user_info(user_id="api_user", roles=["api"], extra={"key_type": "api_key"})
                return None

        class TestAssembler:
            async def assemble(self, request_data):
                return {
                    "trace_id": "test-trace",
                    "request_path": "/api/v1/resource",
                    "request_method": "GET",
                    "protocol": "https",
                    "tags": {"env": "test"},
                }

        coordinator = auth_coordinator(TestExtractor(), TestAuthenticator(), TestAssembler())

        result = await coordinator.process({})

        # Проверяем структуру
        assert isinstance(result, context)
        assert isinstance(result.user, user_info)
        assert isinstance(result.request, request_info)
        assert isinstance(result.environment, environment_info)

        # Проверяем данные пользователя
        assert result.user.user_id == "api_user"
        assert result.user.roles == ["api"]
        assert result.user.extra == {"key_type": "api_key"}

        # Проверяем данные запроса
        assert result.request.trace_id == "test-trace"
        assert result.request.request_path == "/api/v1/resource"
        assert result.request.request_method == "GET"
        assert result.request.protocol == "https"
        assert result.request.tags == {"env": "test"}
