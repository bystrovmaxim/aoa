# tests/resource_managers/test_wrapper_connection_manager.py
"""
Тесты для WrapperConnectionManager — прокси-обёртки, запрещающей управление
транзакциями на вложенных уровнях.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Инстанциирование:
    - WrapperConnectionManager успешно создаётся (get_wrapper_class реализован).
    - Хранит ссылку на оригинальный менеджер.

Запрет транзакций:
    - open() → TransactionProhibitedError.
    - commit() → TransactionProhibitedError.
    - rollback() → TransactionProhibitedError.

Делегирование execute:
    - execute() делегирует в оригинальный менеджер.
    - execute() с параметрами — параметры пробрасываются.
    - execute() при ошибке оригинала — оборачивает в HandleError.

get_wrapper_class:
    - Возвращает WrapperConnectionManager (для повторной обёртки).
    - Синхронный метод (не корутина).

Двойная обёртка (вложенность):
    - WrapperConnectionManager оборачивается повторно через get_wrapper_class.
    - Двойная обёртка запрещает транзакции.
    - Двойная обёртка делегирует execute до оригинала.

Интеграция с ToolsBox._wrap_connections:
    - _wrap_connections корректно оборачивает менеджер.
    - Повторный _wrap_connections на обёрнутом менеджере работает.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from action_machine.core.exceptions import HandleError, TransactionProhibitedError
from action_machine.core.meta_decorator import meta
from action_machine.resource_managers.iconnection_manager import IConnectionManager
from action_machine.resource_managers.wrapper_connection_manager import WrapperConnectionManager

# ═════════════════════════════════════════════════════════════════════════════
# Mock-менеджер соединений для тестов
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Мок-менеджер соединений для тестов")
class MockConnectionManager(IConnectionManager):
    """
    Мок-реализация IConnectionManager для тестирования WrapperConnectionManager.
    Все методы — AsyncMock для проверки вызовов.
    """

    def __init__(self) -> None:
        self.open = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.execute = AsyncMock(return_value="query_result")

    async def open(self) -> None:
        pass  # переопределяется AsyncMock в __init__

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        pass

    def get_wrapper_class(self) -> type[IConnectionManager] | None:
        return WrapperConnectionManager


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_manager() -> MockConnectionManager:
    """Мок-менеджер соединений."""
    return MockConnectionManager()


@pytest.fixture
def wrapper(mock_manager: MockConnectionManager) -> WrapperConnectionManager:
    """WrapperConnectionManager, оборачивающий мок-менеджер."""
    return WrapperConnectionManager(mock_manager)


@pytest.fixture
def double_wrapper(wrapper: WrapperConnectionManager) -> WrapperConnectionManager:
    """Двойная обёртка — WrapperConnectionManager вокруг WrapperConnectionManager."""
    return WrapperConnectionManager(wrapper)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Инстанциирование
# ═════════════════════════════════════════════════════════════════════════════


class TestInstantiation:
    """WrapperConnectionManager успешно создаётся."""

    def test_creates_successfully(self, mock_manager):
        """Экземпляр создаётся без TypeError (get_wrapper_class реализован)."""
        wrapper = WrapperConnectionManager(mock_manager)
        assert wrapper is not None

    def test_stores_original_manager(self, wrapper, mock_manager):
        """Хранит ссылку на оригинальный менеджер."""
        assert wrapper._connection_manager is mock_manager

    def test_is_instance_of_iconnection_manager(self, wrapper):
        """Является экземпляром IConnectionManager."""
        assert isinstance(wrapper, IConnectionManager)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Запрет транзакций
# ═════════════════════════════════════════════════════════════════════════════


class TestTransactionProhibited:
    """Обёртка запрещает управление транзакциями."""

    @pytest.mark.anyio
    async def test_open_raises_prohibited(self, wrapper):
        """open() бросает TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="open недоступен"):
            await wrapper.open()

    @pytest.mark.anyio
    async def test_commit_raises_prohibited(self, wrapper):
        """commit() бросает TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="commit недоступен"):
            await wrapper.commit()

    @pytest.mark.anyio
    async def test_rollback_raises_prohibited(self, wrapper):
        """rollback() бросает TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="rollback недоступен"):
            await wrapper.rollback()

    @pytest.mark.anyio
    async def test_open_does_not_call_original(self, wrapper, mock_manager):
        """open() не вызывает оригинальный менеджер."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.open()
        mock_manager.open.assert_not_called()

    @pytest.mark.anyio
    async def test_commit_does_not_call_original(self, wrapper, mock_manager):
        """commit() не вызывает оригинальный менеджер."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.commit()
        mock_manager.commit.assert_not_called()

    @pytest.mark.anyio
    async def test_rollback_does_not_call_original(self, wrapper, mock_manager):
        """rollback() не вызывает оригинальный менеджер."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.rollback()
        mock_manager.rollback.assert_not_called()


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Делегирование execute
# ═════════════════════════════════════════════════════════════════════════════


class TestExecuteDelegation:
    """execute() делегирует в оригинальный менеджер."""

    @pytest.mark.anyio
    async def test_execute_delegates_to_original(self, wrapper, mock_manager):
        """execute() вызывает execute оригинального менеджера."""
        result = await wrapper.execute("SELECT 1")
        mock_manager.execute.assert_called_once_with("SELECT 1", None)
        assert result == "query_result"

    @pytest.mark.anyio
    async def test_execute_passes_params(self, wrapper, mock_manager):
        """execute() пробрасывает параметры."""
        await wrapper.execute("SELECT * FROM users WHERE id = $1", (42,))
        mock_manager.execute.assert_called_once_with(
            "SELECT * FROM users WHERE id = $1", (42,)
        )

    @pytest.mark.anyio
    async def test_execute_wraps_error_in_handle_error(self, wrapper, mock_manager):
        """execute() оборачивает ошибку оригинала в HandleError."""
        mock_manager.execute.side_effect = RuntimeError("connection lost")

        with pytest.raises(HandleError, match="Ошибка выполнения SQL"):
            await wrapper.execute("SELECT 1")

    @pytest.mark.anyio
    async def test_execute_preserves_original_error_as_cause(self, wrapper, mock_manager):
        """HandleError содержит оригинальную ошибку в __cause__."""
        original_error = RuntimeError("timeout")
        mock_manager.execute.side_effect = original_error

        with pytest.raises(HandleError) as exc_info:
            await wrapper.execute("SELECT 1")

        assert exc_info.value.__cause__ is original_error


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: get_wrapper_class
# ═════════════════════════════════════════════════════════════════════════════


class TestGetWrapperClass:
    """get_wrapper_class() возвращает WrapperConnectionManager."""

    def test_returns_wrapper_class(self, wrapper):
        """Возвращает WrapperConnectionManager для повторной обёртки."""
        result = wrapper.get_wrapper_class()
        assert result is WrapperConnectionManager

    def test_is_synchronous(self, wrapper):
        """Метод синхронный — возвращает класс, не корутину."""
        result = wrapper.get_wrapper_class()
        assert isinstance(result, type)

    def test_returned_class_is_subclass_of_iconnection_manager(self, wrapper):
        """Возвращённый класс — подкласс IConnectionManager."""
        result = wrapper.get_wrapper_class()
        assert issubclass(result, IConnectionManager)


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Двойная обёртка (вложенность уровня 2+)
# ═════════════════════════════════════════════════════════════════════════════


class TestDoubleWrapping:
    """WrapperConnectionManager корректно оборачивается повторно."""

    def test_double_wrapper_creates_successfully(self, wrapper):
        """Двойная обёртка создаётся без ошибок."""
        double = WrapperConnectionManager(wrapper)
        assert double is not None

    def test_double_wrapper_stores_inner_wrapper(self, double_wrapper, wrapper):
        """Двойная обёртка хранит ссылку на внутреннюю обёртку."""
        assert double_wrapper._connection_manager is wrapper

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_open(self, double_wrapper):
        """Двойная обёртка запрещает open()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.open()

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_commit(self, double_wrapper):
        """Двойная обёртка запрещает commit()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.commit()

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_rollback(self, double_wrapper):
        """Двойная обёртка запрещает rollback()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.rollback()

    @pytest.mark.anyio
    async def test_double_wrapper_delegates_execute_to_original(
        self, double_wrapper, mock_manager
    ):
        """execute() через двойную обёртку доходит до оригинального менеджера."""
        result = await double_wrapper.execute("SELECT 1")
        mock_manager.execute.assert_called_once_with("SELECT 1", None)
        assert result == "query_result"

    @pytest.mark.anyio
    async def test_triple_wrapper_works(self, double_wrapper, mock_manager):
        """Тройная обёртка тоже работает — execute доходит до оригинала."""
        triple = WrapperConnectionManager(double_wrapper)
        result = await triple.execute("SELECT 42")
        mock_manager.execute.assert_called_once_with("SELECT 42", None)
        assert result == "query_result"


# ═════════════════════════════════════════════════════════════════════════════
# ТЕСТЫ: Интеграция с _wrap_connections
# ═════════════════════════════════════════════════════════════════════════════


class TestWrapConnectionsIntegration:
    """
    Имитация логики ToolsBox._wrap_connections() — проверка что
    WrapperConnectionManager корректно работает в реальном сценарии обёртки.
    """

    @staticmethod
    def _wrap_connections(connections):
        """Копия логики ToolsBox._wrap_connections для изолированного теста."""
        if connections is None:
            return None
        wrapped = {}
        for key, connection in connections.items():
            wrapper_class = connection.get_wrapper_class()
            if wrapper_class is not None:
                wrapped[key] = wrapper_class(connection)
            else:
                wrapped[key] = connection
        return wrapped

    def test_wraps_mock_manager(self, mock_manager):
        """Оборачивает MockConnectionManager в WrapperConnectionManager."""
        connections = {"db": mock_manager}
        wrapped = self._wrap_connections(connections)

        assert "db" in wrapped
        assert isinstance(wrapped["db"], WrapperConnectionManager)
        assert wrapped["db"]._connection_manager is mock_manager

    def test_wraps_wrapper_again(self, wrapper):
        """Повторная обёртка WrapperConnectionManager работает."""
        connections = {"db": wrapper}
        wrapped = self._wrap_connections(connections)

        assert isinstance(wrapped["db"], WrapperConnectionManager)
        assert wrapped["db"]._connection_manager is wrapper

    @pytest.mark.anyio
    async def test_wrapped_execute_works(self, mock_manager):
        """execute() через обёрнутый менеджер работает."""
        connections = {"db": mock_manager}
        wrapped = self._wrap_connections(connections)

        result = await wrapped["db"].execute("INSERT INTO orders VALUES ($1)", (1,))
        mock_manager.execute.assert_called_once_with(
            "INSERT INTO orders VALUES ($1)", (1,)
        )
        assert result == "query_result"

    @pytest.mark.anyio
    async def test_wrapped_prohibits_transactions(self, mock_manager):
        """Обёрнутый менеджер запрещает транзакции."""
        connections = {"db": mock_manager}
        wrapped = self._wrap_connections(connections)

        with pytest.raises(TransactionProhibitedError):
            await wrapped["db"].open()

        with pytest.raises(TransactionProhibitedError):
            await wrapped["db"].commit()

        with pytest.raises(TransactionProhibitedError):
            await wrapped["db"].rollback()

    @pytest.mark.anyio
    async def test_double_wrap_execute_reaches_original(self, mock_manager):
        """Двойная обёртка через _wrap_connections — execute доходит до оригинала."""
        # Первая обёртка (parent → child)
        wrapped_1 = self._wrap_connections({"db": mock_manager})
        # Вторая обёртка (child → grandchild)
        wrapped_2 = self._wrap_connections({"db": wrapped_1["db"]})

        result = await wrapped_2["db"].execute("SELECT 1")
        mock_manager.execute.assert_called_once_with("SELECT 1", None)
        assert result == "query_result"

    def test_none_connections_returns_none(self):
        """None connections → None."""
        assert self._wrap_connections(None) is None

    def test_empty_connections_returns_empty(self):
        """Пустой dict → пустой dict."""
        result = self._wrap_connections({})
        assert result == {}
