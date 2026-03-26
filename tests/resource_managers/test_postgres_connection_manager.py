# tests/resource_managers/test_postgres_connection_manager.py
"""
Тесты PostgresConnectionManager — реального менеджера соединения с PostgreSQL.

Проверяем:
- Открытие соединения (успех и ошибка)
- Выполнение запросов (execute)
- Фиксацию и откат транзакций (commit/rollback)
- Поведение при отсутствии открытого соединения
- Возврат класса-обёртки
"""


import pytest

from action_machine.core.exceptions import HandleError
from action_machine.resource_managers.wrapper_connection_manager import WrapperConnectionManager


class TestPostgresConnectionManager:
    """Тесты для PostgresConnectionManager."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: open()
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_open_success(self, postgres_manager, mock_asyncpg_connect, mock_asyncpg_connection):
        """open успешно открывает соединение."""
        await postgres_manager.open()

        mock_asyncpg_connect.assert_called_once_with(**postgres_manager._connection_params)
        assert postgres_manager._conn is mock_asyncpg_connection

    @pytest.mark.anyio
    async def test_open_failure_raises_handle_error(self, postgres_manager, monkeypatch):
        """При ошибке подключения выбрасывается HandleError."""

        async def mock_connect_error(**kwargs):
            raise Exception("Connection refused")

        monkeypatch.setattr("asyncpg.connect", mock_connect_error)

        with pytest.raises(HandleError, match="Ошибка подключения к PostgreSQL"):
            await postgres_manager.open()

        assert postgres_manager._conn is None

    # ------------------------------------------------------------------
    # ТЕСТЫ: execute()
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_execute_without_open_raises(self, postgres_manager):
        """execute без открытого соединения вызывает HandleError."""
        with pytest.raises(HandleError, match="Соединение не открыто"):
            await postgres_manager.execute("SELECT 1")

    @pytest.mark.anyio
    async def test_execute_success(self, postgres_manager, mock_asyncpg_connect, mock_asyncpg_connection):
        """execute успешно выполняет запрос."""
        await postgres_manager.open()
        result = await postgres_manager.execute("SELECT 1")

        mock_asyncpg_connection.execute.assert_called_once_with("SELECT 1")
        assert result == "EXECUTE OK"

    @pytest.mark.anyio
    async def test_execute_with_params(self, postgres_manager, mock_asyncpg_connect, mock_asyncpg_connection):
        """execute передаёт параметры в asyncpg."""
        await postgres_manager.open()
        await postgres_manager.execute("SELECT $1", (42,))

        mock_asyncpg_connection.execute.assert_called_once_with("SELECT $1", 42)

    @pytest.mark.anyio
    async def test_execute_raises_handle_error_on_failure(self, postgres_manager, mock_asyncpg_connect, mock_asyncpg_connection):
        """Ошибка выполнения запроса оборачивается в HandleError."""
        await postgres_manager.open()
        mock_asyncpg_connection.execute.side_effect = Exception("SQL error")

        with pytest.raises(HandleError, match="Ошибка выполнения SQL"):
            await postgres_manager.execute("SELECT 1")

    # ------------------------------------------------------------------
    # ТЕСТЫ: commit()
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_commit_without_open_raises(self, postgres_manager):
        """commit без открытого соединения вызывает HandleError."""
        with pytest.raises(HandleError, match="Соединение не открыто"):
            await postgres_manager.commit()

    @pytest.mark.anyio
    async def test_commit_sends_commit_command(self, postgres_manager, mock_asyncpg_connect, mock_asyncpg_connection):
        """commit отправляет SQL-команду COMMIT."""
        await postgres_manager.open()
        await postgres_manager.commit()

        mock_asyncpg_connection.execute.assert_called_once_with("COMMIT")

    @pytest.mark.anyio
    async def test_commit_raises_on_failure(self, postgres_manager, mock_asyncpg_connect, mock_asyncpg_connection):
        """Ошибка при COMMIT оборачивается в HandleError."""
        await postgres_manager.open()
        mock_asyncpg_connection.execute.side_effect = Exception("Commit failed")

        with pytest.raises(HandleError, match="Ошибка при commit"):
            await postgres_manager.commit()

    # ------------------------------------------------------------------
    # ТЕСТЫ: rollback()
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_rollback_without_open_raises(self, postgres_manager):
        """rollback без открытого соединения вызывает HandleError."""
        with pytest.raises(HandleError, match="Соединение не открыто"):
            await postgres_manager.rollback()

    @pytest.mark.anyio
    async def test_rollback_sends_rollback_command(self, postgres_manager, mock_asyncpg_connect, mock_asyncpg_connection):
        """rollback отправляет SQL-команду ROLLBACK."""
        await postgres_manager.open()
        await postgres_manager.rollback()

        mock_asyncpg_connection.execute.assert_called_once_with("ROLLBACK")

    @pytest.mark.anyio
    async def test_rollback_raises_on_failure(self, postgres_manager, mock_asyncpg_connect, mock_asyncpg_connection):
        """Ошибка при ROLLBACK оборачивается в HandleError."""
        await postgres_manager.open()
        mock_asyncpg_connection.execute.side_effect = Exception("Rollback failed")

        with pytest.raises(HandleError, match="Ошибка при rollback"):
            await postgres_manager.rollback()

    # ------------------------------------------------------------------
    # ТЕСТЫ: get_wrapper_class()
    # ------------------------------------------------------------------

    def test_get_wrapper_class_returns_wrapper(self, postgres_manager):
        """get_wrapper_class возвращает WrapperConnectionManager."""
        assert postgres_manager.get_wrapper_class() is WrapperConnectionManager