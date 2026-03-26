# tests/resource_managers/test_wrapper_connection_manager.py
"""
Тесты WrapperConnectionManager — прокси-обёртки, запрещающей управление транзакциями.
Проверяем:
- Вызов open/commit/rollback через прокси → TransactionProhibitedError
- Вызов execute делегируется внутреннему менеджеру
- Ошибки execute оборачиваются в HandleError
"""
from unittest.mock import AsyncMock

import pytest

from action_machine.core.exceptions import HandleError, TransactionProhibitedError
from action_machine.resource_managers.iconnection_manager import IConnectionManager
from action_machine.resource_managers.wrapper_connection_manager import WrapperConnectionManager


# ----------------------------------------------------------------------
# Вспомогательные классы
# ----------------------------------------------------------------------
class MockInnerManager(IConnectionManager):
    """
    Мок внутреннего менеджера соединений.
    Используем отдельные AsyncMock-атрибуты с префиксом _mock_,
    чтобы не конфликтовать с именами методов интерфейса.
    """
    def __init__(self):
        self._mock_open = AsyncMock()
        self._mock_commit = AsyncMock()
        self._mock_rollback = AsyncMock()
        self._mock_execute = AsyncMock(return_value="result")

    async def open(self):
        return await self._mock_open()

    async def commit(self):
        return await self._mock_commit()

    async def rollback(self):
        return await self._mock_rollback()

    async def execute(self, query, params=None):
        return await self._mock_execute(query, params)

    def get_wrapper_class(self):
        return None


class ConcreteWrapperConnectionManager(WrapperConnectionManager):
    """
    Конкретный подкласс WrapperConnectionManager.
    WrapperConnectionManager абстрактный — нельзя создать напрямую.
    get_wrapper_class возвращает None (обёртки второго уровня не нужны).
    """
    def get_wrapper_class(self):
        return None


# ======================================================================
# ТЕСТЫ
# ======================================================================
class TestWrapperConnectionManager:
    """Тесты для WrapperConnectionManager."""

    @pytest.fixture
    def inner(self):
        return MockInnerManager()

    @pytest.fixture
    def wrapper(self, inner):
        return ConcreteWrapperConnectionManager(inner)

    # ------------------------------------------------------------------
    # ТЕСТЫ: Запрещённые операции
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_open_raises_transaction_prohibited(self, wrapper):
        """open через прокси должен кидать TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="Открытие соединения разрешено только"):
            await wrapper.open()

    @pytest.mark.anyio
    async def test_commit_raises_transaction_prohibited(self, wrapper):
        """commit через прокси должен кидать TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="Фиксация транзакции разрешена только"):
            await wrapper.commit()

    @pytest.mark.anyio
    async def test_rollback_raises_transaction_prohibited(self, wrapper):
        """rollback через прокси должен кидать TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="Откат транзакции разрешён только"):
            await wrapper.rollback()

    # ------------------------------------------------------------------
    # ТЕСТЫ: Разрешённые операции
    # ------------------------------------------------------------------
    @pytest.mark.anyio
    async def test_execute_delegates_to_inner(self, wrapper, inner):
        """execute делегируется внутреннему менеджеру и возвращает результат."""
        result = await wrapper.execute("SELECT 1")
        inner._mock_execute.assert_called_once_with("SELECT 1", None)
        assert result == "result"

    @pytest.mark.anyio
    async def test_execute_with_params_delegates(self, wrapper, inner):
        """execute с параметрами делегируется корректно."""
        await wrapper.execute("SELECT $1", (42,))
        inner._mock_execute.assert_called_once_with("SELECT $1", (42,))

    @pytest.mark.anyio
    async def test_execute_wraps_exception_in_handle_error(self, wrapper, inner):
        """Ошибка от внутреннего менеджера оборачивается в HandleError."""
        inner._mock_execute.side_effect = Exception("Inner error")
        with pytest.raises(HandleError, match="Ошибка выполнения SQL"):
            await wrapper.execute("SELECT 1")

    # ------------------------------------------------------------------
    # ТЕСТЫ: Метод get_wrapper_class
    # ------------------------------------------------------------------
    def test_get_wrapper_class_returns_none(self, wrapper):
        """У обёртки get_wrapper_class возвращает None."""
        assert wrapper.get_wrapper_class() is None