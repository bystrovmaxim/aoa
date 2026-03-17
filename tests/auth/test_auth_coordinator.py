"""
Тесты AuthCoordinator — координатора аутентификации.

Проверяем:
- Успешную аутентификацию
- Отсутствие учётных данных
- Неудачную аутентификацию
- Передачу метаданных
- Проброс исключений
- Порядок вызовов
- Минимальные метаданные
- Поле environment
"""

import pytest

from action_machine.Auth.AuthCoordinator import AuthCoordinator
from action_machine.Context.Context import Context
from action_machine.Context.RequestInfo import RequestInfo
from action_machine.Context.UserInfo import UserInfo

from .conftest import MockAuthenticator, MockContextAssembler, MockCredentialExtractor


class TestAuthCoordinator:
    """Тесты координатора аутентификации."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Успешные сценарии
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_auth_success(self, user_info):
        """Успешная аутентификация возвращает Context."""
        # Подготовка
        metadata = {"trace_id": "trace-123", "request_path": "/api/test", "request_method": "POST"}

        extractor = MockCredentialExtractor(return_value={"token": "valid-token"})
        authenticator = MockAuthenticator(return_value=user_info)
        assembler = MockContextAssembler(return_value=metadata)

        coordinator = AuthCoordinator(extractor, authenticator, assembler)

        # Действие
        result = await coordinator.process({"request": "data"})

        # Проверки
        assert result is not None
        assert isinstance(result, Context)
        assert result.user == user_info
        assert result.request.trace_id == "trace-123"
        assert result.request.request_path == "/api/test"

        extractor.extract.assert_called_once_with({"request": "data"})
        authenticator.authenticate.assert_called_once_with({"token": "valid-token"})
        assembler.assemble.assert_called_once_with({"request": "data"})

    @pytest.mark.anyio
    async def test_auth_with_custom_metadata(self, user_info):
        """Метаданные могут быть любым словарем с полями RequestInfo."""
        custom_metadata = {
            "trace_id": "custom-123",
            "client_ip": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            # "extra_field" - убрали, так как его нет в RequestInfo
        }

        extractor = MockCredentialExtractor(return_value={"api_key": "key"})
        authenticator = MockAuthenticator(return_value=user_info)
        assembler = MockContextAssembler(return_value=custom_metadata)

        coordinator = AuthCoordinator(extractor, authenticator, assembler)

        result = await coordinator.process({})

        assert result is not None
        assert result.request.trace_id == "custom-123"
        assert result.request.client_ip == "192.168.1.1"
        assert result.request.user_agent == "Mozilla/5.0"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Неуспешные сценарии
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_auth_no_credentials(self):
        """Нет учётных данных -> возвращает None."""
        extractor = MockCredentialExtractor(return_value={})  # пустой словарь
        authenticator = MockAuthenticator()
        assembler = MockContextAssembler()

        coordinator = AuthCoordinator(extractor, authenticator, assembler)

        result = await coordinator.process({"request": "data"})

        assert result is None
        extractor.extract.assert_called_once()
        authenticator.authenticate.assert_not_called()
        assembler.assemble.assert_not_called()

    @pytest.mark.anyio
    async def test_auth_failed_authentication(self):
        """Аутентификация не удалась -> возвращает None."""
        extractor = MockCredentialExtractor(return_value={"token": "invalid"})
        authenticator = MockAuthenticator(return_value=None)  # неуспех
        assembler = MockContextAssembler()

        coordinator = AuthCoordinator(extractor, authenticator, assembler)

        result = await coordinator.process({"request": "data"})

        assert result is None
        extractor.extract.assert_called_once()
        authenticator.authenticate.assert_called_once_with({"token": "invalid"})
        assembler.assemble.assert_not_called()

    # ------------------------------------------------------------------
    # ТЕСТЫ: Обработка исключений
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_auth_extractor_raises(self):
        """Ошибка в экстракторе пробрасывается наружу."""
        extractor = MockCredentialExtractor()
        extractor.extract.side_effect = ValueError("Ошибка извлечения")

        authenticator = MockAuthenticator()
        assembler = MockContextAssembler()

        coordinator = AuthCoordinator(extractor, authenticator, assembler)

        with pytest.raises(ValueError, match="Ошибка извлечения"):
            await coordinator.process({})

    @pytest.mark.anyio
    async def test_auth_authenticator_raises(self):
        """Ошибка в аутентификаторе пробрасывается наружу."""
        extractor = MockCredentialExtractor(return_value={"token": "test"})
        authenticator = MockAuthenticator()
        authenticator.authenticate.side_effect = ValueError("Ошибка аутентификации")

        assembler = MockContextAssembler()

        coordinator = AuthCoordinator(extractor, authenticator, assembler)

        with pytest.raises(ValueError, match="Ошибка аутентификации"):
            await coordinator.process({})

    @pytest.mark.anyio
    async def test_auth_assembler_raises(self, user_info):
        """Ошибка в сборщике метаданных пробрасывается наружу."""
        extractor = MockCredentialExtractor(return_value={"token": "valid"})
        authenticator = MockAuthenticator(return_value=user_info)
        assembler = MockContextAssembler()
        assembler.assemble.side_effect = ValueError("Ошибка сборки")

        coordinator = AuthCoordinator(extractor, authenticator, assembler)

        with pytest.raises(ValueError, match="Ошибка сборки"):
            await coordinator.process({})

    # ------------------------------------------------------------------
    # ТЕСТЫ: Порядок вызовов
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_auth_preserves_order(self):
        """Компоненты вызываются в правильном порядке."""
        call_order = []

        async def extractor_side(*args):
            call_order.append("extractor")
            return {"token": "valid"}

        async def authenticator_side(*args):
            call_order.append("authenticator")
            return UserInfo(user_id="test")

        async def assembler_side(*args):
            call_order.append("assembler")
            return {"trace_id": "123"}

        extractor = MockCredentialExtractor()
        extractor.extract.side_effect = extractor_side

        authenticator = MockAuthenticator()
        authenticator.authenticate.side_effect = authenticator_side

        assembler = MockContextAssembler()
        assembler.assemble.side_effect = assembler_side

        coordinator = AuthCoordinator(extractor, authenticator, assembler)

        await coordinator.process({})

        assert call_order == ["extractor", "authenticator", "assembler"]

    # ------------------------------------------------------------------
    # ТЕСТЫ: Минимальные метаданные
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_auth_with_minimal_metadata(self, user_info):
        """Минимальные метаданные (пустой словарь) создают RequestInfo с полями по умолчанию."""
        extractor = MockCredentialExtractor(return_value={"token": "x"})
        authenticator = MockAuthenticator(return_value=user_info)
        assembler = MockContextAssembler(return_value={})  # пустой словарь

        coordinator = AuthCoordinator(extractor, authenticator, assembler)

        result = await coordinator.process({})

        assert result is not None
        assert result.user == user_info
        assert isinstance(result.request, RequestInfo)
        # Все поля RequestInfo должны быть None по умолчанию
        assert result.request.trace_id is None
        assert result.request.request_path is None

    @pytest.mark.anyio
    async def test_auth_environment_default(self, user_info):
        """Поле environment в Context заполняется значением по умолчанию (EnvironmentInfo)."""
        extractor = MockCredentialExtractor(return_value={"token": "x"})
        authenticator = MockAuthenticator(return_value=user_info)
        assembler = MockContextAssembler(return_value={})

        coordinator = AuthCoordinator(extractor, authenticator, assembler)

        result = await coordinator.process({})

        assert result is not None
        # AuthCoordinator передаёт environment=None, но Context.__init__
        # подставляет EnvironmentInfo() по умолчанию
        from action_machine.Context.EnvironmentInfo import EnvironmentInfo

        assert isinstance(result.environment, EnvironmentInfo)
