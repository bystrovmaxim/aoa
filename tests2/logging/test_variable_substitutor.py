# tests2/resource_managers/test_postgres_connection_manager.py
"""
Тесты PostgresConnectionManager — реального менеджера соединения с PostgreSQL.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

PostgresConnectionManager — конкретная реализация IConnectionManager для
PostgreSQL на базе asyncpg. Выполняет непосредственную работу с базой данных:
открытие соединения, выполнение SQL-запросов, управление транзакциями.

Поддерживает режим rollup: при rollup=True метод commit() выполняет ROLLBACK
вместо COMMIT, что позволяет безопасно тестировать на production-базе.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Конструктор:
    - Сохраняет connection_params и rollup.
    - Прокидывает rollup в IConnectionManager.

open():
    - Успешное открытие соединения через asyncpg.connect().
    - Ошибка подключения → HandleError.

execute():
    - Без открытого соединения → HandleError.
    - Успешное выполнение запроса, возврат результата.
    - Передача параметров в запрос.
    - Ошибка выполнения → HandleError.

commit():
    - Без открытого соединения → HandleError.
    - При rollup=False → отправка COMMIT.
    - При rollup=True → вызов rollback() вместо COMMIT.
    - Ошибка COMMIT → HandleError.

rollback():
    - Без открытого соединения → HandleError.
    - Успешный ROLLBACK.
    - Ошибка ROLLBACK → HandleError.

get_wrapper_class():
    - Возвращает WrapperConnectionManager.

Поддержка rollup:
    - rollup передаётся в super().__init__().
    - При rollup=True commit() перехватывается в IConnectionManager.commit().
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from action_machine.contrib.postgres.postgres_connection_manager import PostgresConnectionManager
from action_machine.core.exceptions import HandleError
from action_machine.resource_managers.wrapper_connection_manager import WrapperConnectionManager


@pytest.fixture
def mock_asyncpg_connection() -> AsyncMock:
    """Мок соединения asyncpg."""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="EXECUTE OK")
    return conn


@pytest.fixture
def mock_asyncpg_connect(mock_asyncpg_connection: AsyncMock, monkeypatch) -> AsyncMock:
    """Мок функции asyncpg.connect."""
    mock = AsyncMock(return_value=mock_asyncpg_connection)
    monkeypatch.setattr("asyncpg.connect", mock)
    return mock


@pytest.fixture
def connection_params() -> dict:
    """Параметры подключения к БД."""
    return {
        "host": "localhost",
        "port": 5432,
        "user": "test",
        "password": "test",
        "database": "testdb",
    }


@pytest.fixture
def postgres_manager(connection_params: dict) -> PostgresConnectionManager:
    """Экземпляр PostgresConnectionManager с тестовыми параметрами."""
    return PostgresConnectionManager(connection_params)


# ======================================================================
# ТЕСТЫ: Конструктор
# ======================================================================

class TestConstructor:
    """Создание PostgresConnectionManager."""

    def test_stores_connection_params(self, postgres_manager: PostgresConnectionManager) -> None:
        """Параметры подключения сохраняются в _connection_params."""
        assert postgres_manager._connection_params == {
            "host": "localhost", "port": 5432, "user": "test",
            "password": "test", "database": "testdb",
        }

    def test_rollup_default_false(self) -> None:
        """По умолчанию rollup=False."""
        manager = PostgresConnectionManager({"host": "localhost"})
        assert manager.rollup is False

    def test_rollup_true_passed_to_super(self) -> None:
        """rollup=True передаётся в IConnectionManager."""
        manager = PostgresConnectionManager({"host": "localhost"}, rollup=True)
        assert manager.rollup is True

    def test_conn_initial_none(self, postgres_manager: PostgresConnectionManager) -> None:
        """Изначально _conn = None."""
        assert postgres_manager._conn is None


# ======================================================================
# ТЕСТЫ: open()
# ======================================================================

class TestOpen:
    """Открытие соединения."""

    @pytest.mark.anyio
    async def test_open_success(
        self,
        postgres_manager: PostgresConnectionManager,
        mock_asyncpg_connect: AsyncMock,
        mock_asyncpg_connection: AsyncMock,
    ) -> None:
        """open успешно открывает соединение."""
        await postgres_manager.open()

        mock_asyncpg_connect.assert_called_once_with(**postgres_manager._connection_params)
        assert postgres_manager._conn is mock_asyncpg_connection

    @pytest.mark.anyio
    async def test_open_failure_raises_handle_error(
        self,
        postgres_manager: PostgresConnectionManager,
        monkeypatch,
    ) -> None:
        """При ошибке подключения выбрасывается HandleError."""
        async def mock_connect_error(**kwargs):
            raise Exception("Connection refused")

        monkeypatch.setattr("asyncpg.connect", mock_connect_error)

        with pytest.raises(HandleError, match="Ошибка подключения к PostgreSQL"):
            await postgres_manager.open()

        assert postgres_manager._conn is None


# ======================================================================
# ТЕСТЫ: execute()
# ======================================================================

class TestExecute:
    """Выполнение SQL-запросов."""

    @pytest.mark.anyio
    async def test_execute_without_open_raises(
        self,
        postgres_manager: PostgresConnectionManager,
    ) -> None:
        """execute без открытого соединения вызывает HandleError."""
        with pytest.raises(HandleError, match="Соединение не открыто"):
            await postgres_manager.execute("SELECT 1")

    @pytest.mark.anyio
    async def test_execute_success(
        self,
        postgres_manager: PostgresConnectionManager,
        mock_asyncpg_connect: AsyncMock,
        mock_asyncpg_connection: AsyncMock,
    ) -> None:
        """execute успешно выполняет запрос."""
        await postgres_manager.open()
        result = await postgres_manager.execute("SELECT 1")

        mock_asyncpg_connection.execute.assert_called_once_with("SELECT 1")
        assert result == "EXECUTE OK"

    @pytest.mark.anyio
    async def test_execute_with_params(
        self,
        postgres_manager: PostgresConnectionManager,
        mock_asyncpg_connect: AsyncMock,
        mock_asyncpg_connection: AsyncMock,
    ) -> None:
        """execute передаёт параметры в asyncpg."""
        await postgres_manager.open()
        await postgres_manager.execute("SELECT $1", (42,))

        mock_asyncpg_connection.execute.assert_called_once_with("SELECT $1", 42)

    @pytest.mark.anyio
    async def test_execute_raises_handle_error_on_failure(
        self,
        postgres_manager: PostgresConnectionManager,
        mock_asyncpg_connect: AsyncMock,
        mock_asyncpg_connection: AsyncMock,
    ) -> None:
        """Ошибка выполнения запроса оборачивается в HandleError."""
        await postgres_manager.open()
        mock_asyncpg_connection.execute.side_effect = Exception("SQL error")

        with pytest.raises(HandleError, match="Ошибка выполнения SQL"):
            await postgres_manager.execute("SELECT 1")


# ======================================================================
# ТЕСТЫ: commit()
# ======================================================================

class TestCommit:
    """Фиксация транзакции."""

    @pytest.mark.anyio
    async def test_commit_without_open_raises(
        self,
        postgres_manager: PostgresConnectionManager,
    ) -> None:
        """commit без открытого соединения вызывает HandleError."""
        with pytest.raises(HandleError, match="Соединение не открыто"):
            await postgres_manager.commit()

    @pytest.mark.anyio
    async def test_commit_sends_commit_command(
        self,
        postgres_manager: PostgresConnectionManager,
        mock_asyncpg_connect: AsyncMock,
        mock_asyncpg_connection: AsyncMock,
    ) -> None:
        """commit отправляет SQL-команду COMMIT."""
        await postgres_manager.open()
        await postgres_manager.commit()

        mock_asyncpg_connection.execute.assert_called_once_with("COMMIT")

    @pytest.mark.anyio
    async def test_commit_rollup_true_calls_rollback(
        self,
        connection_params: dict,
        mock_asyncpg_connect: AsyncMock,
        mock_asyncpg_connection: AsyncMock,
    ) -> None:
        """При rollup=True commit() вызывает rollback() вместо COMMIT."""
        manager = PostgresConnectionManager(connection_params, rollup=True)
        await manager.open()
        await manager.commit()

        # При rollup=True IConnectionManager.commit() вызывает rollback()
        # Rollback отправляет ROLLBACK
        mock_asyncpg_connection.execute.assert_called_once_with("ROLLBACK")

    @pytest.mark.anyio
    async def test_commit_raises_on_failure(
        self,
        postgres_manager: PostgresConnectionManager,
        mock_asyncpg_connect: AsyncMock,
        mock_asyncpg_connection: AsyncMock,
    ) -> None:
        """Ошибка при COMMIT оборачивается в HandleError."""
        await postgres_manager.open()
        mock_asyncpg_connection.execute.side_effect = Exception("Commit failed")

        with pytest.raises(HandleError, match="Ошибка при commit"):
            await postgres_manager.commit()


# ======================================================================
# ТЕСТЫ: rollback()
# ======================================================================

class TestRollback:
    """Откат транзакции."""

    @pytest.mark.anyio
    async def test_rollback_without_open_raises(
        self,
        postgres_manager: PostgresConnectionManager,
    ) -> None:
        """rollback без открытого соединения вызывает HandleError."""
        with pytest.raises(HandleError, match="Соединение не открыто"):
            await postgres_manager.rollback()

    @pytest.mark.anyio
    async def test_rollback_sends_rollback_command(
        self,
        postgres_manager: PostgresConnectionManager,
        mock_asyncpg_connect: AsyncMock,
        mock_asyncpg_connection: AsyncMock,
    ) -> None:
        """rollback отправляет SQL-команду ROLLBACK."""
        await postgres_manager.open()
        await postgres_manager.rollback()

        mock_asyncpg_connection.execute.assert_called_once_with("ROLLBACK")

    @pytest.mark.anyio
    async def test_rollback_raises_on_failure(
        self,
        postgres_manager: PostgresConnectionManager,
        mock_asyncpg_connect: AsyncMock,
        mock_asyncpg_connection: AsyncMock,
    ) -> None:
        """Ошибка при ROLLBACK оборачивается в HandleError."""
        await postgres_manager.open()
        mock_asyncpg_connection.execute.side_effect = Exception("Rollback failed")

        with pytest.raises(HandleError, match="Ошибка при rollback"):
            await postgres_manager.rollback()


# ======================================================================
# ТЕСТЫ: get_wrapper_class()
# ======================================================================

class TestGetWrapperClass:
    """Возврат класса-обёртки."""

    def test_returns_wrapper_connection_manager(self, postgres_manager: PostgresConnectionManager) -> None:
        """get_wrapper_class возвращает WrapperConnectionManager."""
        assert postgres_manager.get_wrapper_class() is WrapperConnectionManager


# ======================================================================
# ТЕСТЫ: Поддержка rollup через свойство
# ======================================================================

class TestRollupProperty:
    """Свойство rollup отражает режим автоотката."""

    def test_rollup_false_by_default(self) -> None:
        """По умолчанию rollup=False."""
        manager = PostgresConnectionManager({"host": "localhost"})
        assert manager.rollup is False

    def test_rollup_true_when_set(self) -> None:
        """rollup=True передаётся в конструктор."""
        manager = PostgresConnectionManager({"host": "localhost"}, rollup=True)
        assert manager.rollup is True