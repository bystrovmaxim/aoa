# tests/resource_managers/conftest.py
"""
Фикстуры для тестирования ресурсных менеджеров.
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.contrib.postgres.postgres_connection_manager import PostgresConnectionManager


@pytest.fixture
def mock_asyncpg_connection():
    """Мок соединения asyncpg."""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value="EXECUTE OK")
    return conn


@pytest.fixture
def mock_asyncpg_connect(mock_asyncpg_connection, monkeypatch):
    """Мок функции asyncpg.connect."""
    mock = AsyncMock(return_value=mock_asyncpg_connection)
    monkeypatch.setattr("asyncpg.connect", mock)
    return mock


@pytest.fixture
def connection_params():
    """Параметры подключения к БД."""
    return {
        "host": "localhost",
        "port": 5432,
        "user": "test",
        "password": "test",
        "database": "testdb",
    }


@pytest.fixture
def postgres_manager(connection_params):
    """Экземпляр PostgresConnectionManager с тестовыми параметрами."""
    return PostgresConnectionManager(connection_params)


@pytest.fixture
def real_connection_manager(postgres_manager, mock_asyncpg_connect, mock_asyncpg_connection):
    """PostgresConnectionManager с уже открытым соединением."""
    return postgres_manager