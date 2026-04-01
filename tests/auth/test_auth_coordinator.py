# tests/auth/test_auth_coordinator.py
"""
Тесты AuthCoordinator и NoAuthCoordinator — координаторы аутентификации.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

AuthCoordinator — координатор полного цикла аутентификации. Объединяет
три компонента в последовательную цепочку:

    CredentialExtractor.extract(request) → credentials
    Authenticator.authenticate(credentials) → UserInfo
    ContextAssembler.assemble(request) → RequestInfo metadata

Результат — Context с аутентифицированным пользователем и метаданными
запроса. Если любой шаг возвращает None/пустой результат — весь процесс
возвращает None (аутентификация не пройдена).

NoAuthCoordinator — провайдер для открытых API. Всегда возвращает
анонимный Context без пользователя и ролей. Реализует тот же интерфейс
(async process(request_data) → Context), что и AuthCoordinator.

Оба координатора передаются в BaseAdapter как обязательный параметр
auth_coordinator. Разработчик не может «забыть» подключить аутентификацию —
для открытых API используется NoAuthCoordinator как явная декларация.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

AuthCoordinator — успешная аутентификация:
    - Все три компонента возвращают данные → Context с UserInfo и RequestInfo.

AuthCoordinator — неуспешная аутентификация:
    - Extractor возвращает пустой dict → None (нет credentials).
    - Authenticator возвращает None → None (credentials невалидны).

NoAuthCoordinator:
    - Всегда возвращает Context (не None).
    - UserInfo: user_id=None, roles=[].
    - Игнорирует request_data.

Интерфейсная совместимость:
    - Оба координатора имеют async process(request_data) → Context|None.
"""

import pytest

from action_machine.auth.auth_coordinator import AuthCoordinator
from action_machine.auth.authenticator import Authenticator
from action_machine.auth.context_assembler import ContextAssembler
from action_machine.auth.credential_extractor import CredentialExtractor
from action_machine.auth.no_auth_coordinator import NoAuthCoordinator
from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo

# ═════════════════════════════════════════════════════════════════════════════
# Мок-реализации компонентов аутентификации
# ═════════════════════════════════════════════════════════════════════════════


class _MockExtractor(CredentialExtractor):
    """
    Мок-экстрактор, возвращающий заданные credentials.

    Если credentials_to_return — пустой dict, имитирует ситуацию
    «учётные данные не найдены в запросе» (например, нет заголовка
    Authorization).
    """

    def __init__(self, credentials_to_return: dict | None = None):
        self._credentials = credentials_to_return if credentials_to_return is not None else {}

    async def extract(self, request_data):
        return self._credentials


class _MockAuthenticator(Authenticator):
    """
    Мок-аутентификатор, возвращающий заданный UserInfo.

    Если user_to_return=None, имитирует невалидные credentials
    (например, просроченный токен).
    """

    def __init__(self, user_to_return: UserInfo | None = None):
        self._user = user_to_return

    async def authenticate(self, credentials):
        return self._user


class _MockAssembler(ContextAssembler):
    """
    Мок-сборщик метаданных запроса.

    Возвращает фиксированный словарь с trace_id, request_path
    и другими полями для создания RequestInfo.
    """

    def __init__(self, metadata_to_return: dict | None = None):
        self._metadata = metadata_to_return or {
            "trace_id": "test-trace-001",
            "request_path": "/api/v1/test",
        }

    async def assemble(self, request_data):
        return self._metadata


# ═════════════════════════════════════════════════════════════════════════════
# AuthCoordinator — успешная аутентификация
# ═════════════════════════════════════════════════════════════════════════════


class TestAuthCoordinatorSuccess:
    """Полный цикл аутентификации — все компоненты возвращают данные."""

    @pytest.mark.asyncio
    async def test_full_cycle_returns_context(self) -> None:
        """
        Все три компонента возвращают данные → Context с UserInfo и RequestInfo.

        Цепочка:
        1. Extractor.extract() → {"api_key": "secret-123"}
        2. Authenticator.authenticate(credentials) → UserInfo(user_id="u1", roles=["admin"])
        3. Assembler.assemble() → {"trace_id": "t1", "request_path": "/api"}
        4. Результат → Context(user=UserInfo, request=RequestInfo)
        """
        # Arrange — три компонента с валидными данными
        extractor = _MockExtractor({"api_key": "secret-123"})
        authenticator = _MockAuthenticator(
            UserInfo(user_id="u1", roles=["admin"]),
        )
        assembler = _MockAssembler({
            "trace_id": "trace-full",
            "request_path": "/api/v1/orders",
        })

        coordinator = AuthCoordinator(
            extractor=extractor,
            auth_instance=authenticator,
            assembler=assembler,
        )

        # Act — полный цикл аутентификации
        result = await coordinator.process({"raw_request": "data"})

        # Assert — Context содержит аутентифицированного пользователя
        assert result is not None
        assert isinstance(result, Context)
        assert result.user.user_id == "u1"
        assert result.user.roles == ["admin"]
        assert result.request.trace_id == "trace-full"
        assert result.request.request_path == "/api/v1/orders"

    @pytest.mark.asyncio
    async def test_user_info_preserved_in_context(self) -> None:
        """
        UserInfo из Authenticator передаётся в Context без изменений.

        Все поля UserInfo (user_id, roles, extra) доступны через
        context.user.
        """
        # Arrange — UserInfo с extra
        user = UserInfo(user_id="agent_007", roles=["spy"], extra={"org": "mi6"})
        extractor = _MockExtractor({"token": "valid"})
        authenticator = _MockAuthenticator(user)
        assembler = _MockAssembler()

        coordinator = AuthCoordinator(
            extractor=extractor,
            auth_instance=authenticator,
            assembler=assembler,
        )

        # Act
        result = await coordinator.process(None)

        # Assert — UserInfo полностью сохранён
        assert result is not None
        assert result.user.user_id == "agent_007"
        assert result.user.roles == ["spy"]
        assert result.user.extra == {"org": "mi6"}


# ═════════════════════════════════════════════════════════════════════════════
# AuthCoordinator — неуспешная аутентификация
# ═════════════════════════════════════════════════════════════════════════════


class TestAuthCoordinatorFailure:
    """Аутентификация прервана на одном из шагов → None."""

    @pytest.mark.asyncio
    async def test_empty_credentials_returns_none(self) -> None:
        """
        Extractor возвращает пустой dict → process() возвращает None.

        Пустые credentials означают, что запрос не содержит данных
        аутентификации (нет заголовка Authorization, нет cookie и т.д.).
        Authenticator не вызывается.
        """
        # Arrange — extractor возвращает пустой dict
        extractor = _MockExtractor({})
        authenticator = _MockAuthenticator(UserInfo(user_id="should_not_reach"))
        assembler = _MockAssembler()

        coordinator = AuthCoordinator(
            extractor=extractor,
            auth_instance=authenticator,
            assembler=assembler,
        )

        # Act — процесс прерывается на первом шаге
        result = await coordinator.process(None)

        # Assert — None, аутентификация не пройдена
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticator_returns_none(self) -> None:
        """
        Authenticator возвращает None → process() возвращает None.

        Credentials переданы, но невалидны (просроченный токен,
        неверный пароль, заблокированный аккаунт). Assembler не вызывается.
        """
        # Arrange — extractor возвращает credentials, authenticator → None
        extractor = _MockExtractor({"token": "expired-token"})
        authenticator = _MockAuthenticator(None)
        assembler = _MockAssembler()

        coordinator = AuthCoordinator(
            extractor=extractor,
            auth_instance=authenticator,
            assembler=assembler,
        )

        # Act — процесс прерывается на втором шаге
        result = await coordinator.process(None)

        # Assert — None, credentials невалидны
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# NoAuthCoordinator
# ═════════════════════════════════════════════════════════════════════════════


class TestNoAuthCoordinator:
    """NoAuthCoordinator — анонимный контекст для открытых API."""

    @pytest.mark.asyncio
    async def test_returns_context_not_none(self) -> None:
        """
        NoAuthCoordinator.process() всегда возвращает Context (не None).

        В отличие от AuthCoordinator, который может вернуть None
        при неуспешной аутентификации, NoAuthCoordinator гарантирует
        Context для каждого запроса.
        """
        # Arrange
        coordinator = NoAuthCoordinator()

        # Act
        result = await coordinator.process({"any": "data"})

        # Assert — всегда Context, не None
        assert result is not None
        assert isinstance(result, Context)

    @pytest.mark.asyncio
    async def test_anonymous_user(self) -> None:
        """
        NoAuthCoordinator создаёт анонимного пользователя.

        UserInfo: user_id=None, roles=[]. Действия с @check_roles(ROLE_NONE)
        проходят проверку, действия с конкретными ролями — отклоняются.
        """
        # Arrange
        coordinator = NoAuthCoordinator()

        # Act
        result = await coordinator.process(None)

        # Assert — анонимный пользователь
        assert result.user.user_id is None
        assert result.user.roles == []

    @pytest.mark.asyncio
    async def test_ignores_request_data(self) -> None:
        """
        NoAuthCoordinator игнорирует request_data.

        Вызов process() с любым аргументом (None, dict, строка)
        возвращает одинаковый анонимный Context.
        """
        # Arrange
        coordinator = NoAuthCoordinator()

        # Act — разные типы request_data
        result_none = await coordinator.process(None)
        result_dict = await coordinator.process({"key": "value"})
        result_str = await coordinator.process("raw_request")

        # Assert — все три возвращают анонимный Context
        assert result_none.user.user_id is None
        assert result_dict.user.user_id is None
        assert result_str.user.user_id is None

    @pytest.mark.asyncio
    async def test_each_call_returns_new_context(self) -> None:
        """
        Каждый вызов process() возвращает новый экземпляр Context.

        Контексты не разделяются между запросами — полная изоляция.
        """
        # Arrange
        coordinator = NoAuthCoordinator()

        # Act — два вызова
        ctx1 = await coordinator.process(None)
        ctx2 = await coordinator.process(None)

        # Assert — два разных объекта
        assert ctx1 is not ctx2


# ═════════════════════════════════════════════════════════════════════════════
# Интерфейсная совместимость
# ═════════════════════════════════════════════════════════════════════════════


class TestInterfaceCompatibility:
    """Оба координатора имеют одинаковый интерфейс process()."""

    def test_auth_coordinator_has_process(self) -> None:
        """
        AuthCoordinator имеет асинхронный метод process().
        """
        # Arrange
        coordinator = AuthCoordinator(
            extractor=_MockExtractor(),
            auth_instance=_MockAuthenticator(),
            assembler=_MockAssembler(),
        )

        # Act & Assert — метод существует
        assert hasattr(coordinator, "process")
        assert callable(coordinator.process)

    def test_no_auth_coordinator_has_process(self) -> None:
        """
        NoAuthCoordinator имеет асинхронный метод process().
        """
        # Arrange
        coordinator = NoAuthCoordinator()

        # Act & Assert — метод существует
        assert hasattr(coordinator, "process")
        assert callable(coordinator.process)

    @pytest.mark.asyncio
    async def test_both_accept_any_request_data(self) -> None:
        """
        Оба координатора принимают произвольный request_data.

        process() принимает Any — тип зависит от протокола:
        FastAPI Request, MCP tool call dict, None и т.д.
        """
        # Arrange
        auth = AuthCoordinator(
            extractor=_MockExtractor({"key": "val"}),
            auth_instance=_MockAuthenticator(UserInfo(user_id="u1")),
            assembler=_MockAssembler(),
        )
        no_auth = NoAuthCoordinator()

        # Act — оба принимают None
        auth_result = await auth.process(None)
        no_auth_result = await no_auth.process(None)

        # Assert — оба вернули результат
        assert auth_result is not None
        assert no_auth_result is not None
