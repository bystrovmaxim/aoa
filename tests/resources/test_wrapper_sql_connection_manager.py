# tests/resources/test_wrapper_sql_connection_manager.py
"""
Тесты WrapperSqlConnectionManager — прокси-обёртки, запрещающей управление
транзакциями на вложенных уровнях.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

WrapperSqlConnectionManager — прокси-обёртка вокруг реального SqlConnectionManager.
Создаётся автоматически при передаче connections в дочерние действия через
ToolsBox.run(). Обёртка запрещает дочернему действию управлять жизненным
циклом ресурса (open, begin, commit, rollback), но разрешает выполнять запросы
(execute). Флаг rollup наследуется от оригинального менеджера.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Конструктор:
    - Хранит ссылку на оригинальный менеджер.
    - Наследует rollup от оригинального менеджера.

Запрет транзакций:
    - open() → TransactionProhibitedError.
    - begin() → TransactionProhibitedError.
    - commit() → TransactionProhibitedError.
    - rollback() → TransactionProhibitedError.

Делегирование execute:
    - execute() делегирует в оригинальный менеджер.
    - execute() с параметрами — параметры пробрасываются.
    - execute() при ошибке оригинала — оборачивает в HandleError.

get_wrapper_class:
    - Возвращает WrapperSqlConnectionManager (для повторной обёртки).
    - Синхронный метод.

Двойная обёртка (вложенность):
    - WrapperSqlConnectionManager оборачивается повторно через get_wrapper_class.
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

from action_machine.model.exceptions import HandleError, TransactionProhibitedError
from action_machine.resources.sql_connection_manager import SqlConnectionManager
from action_machine.resources.wrapper_sql_connection_manager import (
    WrapperSqlConnectionManager,
)

# ======================================================================
# Mock-менеджер соединений для тестов
# ======================================================================

class MockConnectionManager(SqlConnectionManager):
    """
    Мок-реализация SqlConnectionManager для тестирования WrapperSqlConnectionManager.
    Все методы — AsyncMock для проверки вызовов.
    """

    def __init__(self) -> None:
        self.open = AsyncMock()
        self.begin = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.execute = AsyncMock(return_value="query_result")

    async def open(self) -> None:
        pass  # переопределяется AsyncMock в __init__

    async def begin(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def execute(self, query: str, params: tuple[Any, ...] | None = None) -> Any:
        pass

    def get_wrapper_class(self) -> type[SqlConnectionManager] | None:
        return WrapperSqlConnectionManager


# ======================================================================
# Фикстуры
# ======================================================================

@pytest.fixture
def mock_manager() -> MockConnectionManager:
    """Мок-менеджер соединений."""
    return MockConnectionManager()


@pytest.fixture
def wrapper(mock_manager: MockConnectionManager) -> WrapperSqlConnectionManager:
    """WrapperSqlConnectionManager, оборачивающий мок-менеджер."""
    return WrapperSqlConnectionManager(mock_manager)


@pytest.fixture
def double_wrapper(wrapper: WrapperSqlConnectionManager) -> WrapperSqlConnectionManager:
    """Двойная обёртка — WrapperSqlConnectionManager вокруг WrapperSqlConnectionManager."""
    return WrapperSqlConnectionManager(wrapper)


# ======================================================================
# ТЕСТЫ: Конструктор
# ======================================================================

class TestConstructor:
    """WrapperSqlConnectionManager успешно создаётся."""

    def test_creates_successfully(self, mock_manager: MockConnectionManager) -> None:
        """Экземпляр создаётся без ошибок."""
        w = WrapperSqlConnectionManager(mock_manager)
        assert w is not None

    def test_stores_original_manager(self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager) -> None:
        """Хранит ссылку на оригинальный менеджер."""
        assert wrapper._connection_manager is mock_manager

    def test_inherits_rollup_from_original(self, mock_manager: MockConnectionManager) -> None:
        """rollup наследуется от оригинального менеджера."""
        mock_manager._rollup = True
        wrapper = WrapperSqlConnectionManager(mock_manager)
        assert wrapper.rollup is True

    def test_is_instance_of_sql_connection_manager(self, wrapper: WrapperSqlConnectionManager) -> None:
        """Является экземпляром SqlConnectionManager."""
        assert isinstance(wrapper, SqlConnectionManager)


# ======================================================================
# ТЕСТЫ: Запрет транзакций
# ======================================================================

class TestTransactionProhibited:
    """Обёртка запрещает управление транзакциями."""

    @pytest.mark.anyio
    async def test_open_raises_prohibited(self, wrapper: WrapperSqlConnectionManager) -> None:
        """open() бросает TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="open недоступен"):
            await wrapper.open()

    @pytest.mark.anyio
    async def test_commit_raises_prohibited(self, wrapper: WrapperSqlConnectionManager) -> None:
        """commit() бросает TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="commit недоступен"):
            await wrapper.commit()

    @pytest.mark.anyio
    async def test_rollback_raises_prohibited(self, wrapper: WrapperSqlConnectionManager) -> None:
        """rollback() бросает TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="rollback недоступен"):
            await wrapper.rollback()

    @pytest.mark.anyio
    async def test_begin_raises_prohibited(self, wrapper: WrapperSqlConnectionManager) -> None:
        """begin() бросает TransactionProhibitedError."""
        with pytest.raises(TransactionProhibitedError, match="begin недоступен"):
            await wrapper.begin()

    @pytest.mark.anyio
    async def test_open_does_not_call_original(self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager) -> None:
        """open() не вызывает оригинальный менеджер."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.open()
        mock_manager.open.assert_not_called()

    @pytest.mark.anyio
    async def test_commit_does_not_call_original(self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager) -> None:
        """commit() не вызывает оригинальный менеджер."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.commit()
        mock_manager.commit.assert_not_called()

    @pytest.mark.anyio
    async def test_rollback_does_not_call_original(self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager) -> None:
        """rollback() не вызывает оригинальный менеджер."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.rollback()
        mock_manager.rollback.assert_not_called()

    @pytest.mark.anyio
    async def test_begin_does_not_call_original(self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager) -> None:
        """begin() не вызывает оригинальный менеджер."""
        with pytest.raises(TransactionProhibitedError):
            await wrapper.begin()
        mock_manager.begin.assert_not_called()


# ======================================================================
# ТЕСТЫ: Делегирование execute
# ======================================================================

class TestExecuteDelegation:
    """execute() делегирует в оригинальный менеджер."""

    @pytest.mark.anyio
    async def test_execute_delegates_to_original(
        self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager,
    ) -> None:
        """execute() вызывает execute оригинального менеджера."""
        result = await wrapper.execute("SELECT 1")
        mock_manager.execute.assert_called_once_with("SELECT 1", None)
        assert result == "query_result"

    @pytest.mark.anyio
    async def test_execute_passes_params(
        self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager,
    ) -> None:
        """execute() пробрасывает параметры."""
        await wrapper.execute("SELECT * FROM users WHERE id = $1", (42,))
        mock_manager.execute.assert_called_once_with(
            "SELECT * FROM users WHERE id = $1", (42,)
        )

    @pytest.mark.anyio
    async def test_execute_wraps_error_in_handle_error(
        self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager,
    ) -> None:
        """execute() оборачивает ошибку оригинала в HandleError."""
        mock_manager.execute.side_effect = RuntimeError("connection lost")

        with pytest.raises(HandleError, match="Ошибка выполнения SQL"):
            await wrapper.execute("SELECT 1")

    @pytest.mark.anyio
    async def test_execute_preserves_original_error_as_cause(
        self, wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager,
    ) -> None:
        """HandleError содержит оригинальную ошибку в __cause__."""
        original_error = RuntimeError("timeout")
        mock_manager.execute.side_effect = original_error

        with pytest.raises(HandleError) as exc_info:
            await wrapper.execute("SELECT 1")

        assert exc_info.value.__cause__ is original_error


# ======================================================================
# ТЕСТЫ: get_wrapper_class
# ======================================================================

class TestGetWrapperClass:
    """get_wrapper_class() возвращает WrapperSqlConnectionManager."""

    def test_returns_wrapper_class(self, wrapper: WrapperSqlConnectionManager) -> None:
        """Возвращает WrapperSqlConnectionManager для повторной обёртки."""
        result = wrapper.get_wrapper_class()
        assert result is WrapperSqlConnectionManager

    def test_is_synchronous(self, wrapper: WrapperSqlConnectionManager) -> None:
        """Метод синхронный — возвращает класс, не корутину."""
        result = wrapper.get_wrapper_class()
        assert isinstance(result, type)

    def test_returned_class_is_subclass_of_sql_connection_manager(self, wrapper: WrapperSqlConnectionManager) -> None:
        """Возвращённый класс — подкласс SqlConnectionManager."""
        result = wrapper.get_wrapper_class()
        assert issubclass(result, SqlConnectionManager)


# ======================================================================
# ТЕСТЫ: Двойная обёртка (вложенность уровня 2+)
# ======================================================================

class TestDoubleWrapping:
    """WrapperSqlConnectionManager корректно оборачивается повторно."""

    def test_double_wrapper_creates_successfully(self, wrapper: WrapperSqlConnectionManager) -> None:
        """Двойная обёртка создаётся без ошибок."""
        double = WrapperSqlConnectionManager(wrapper)
        assert double is not None

    def test_double_wrapper_stores_inner_wrapper(
        self, double_wrapper: WrapperSqlConnectionManager, wrapper: WrapperSqlConnectionManager,
    ) -> None:
        """Двойная обёртка хранит ссылку на внутреннюю обёртку."""
        assert double_wrapper._connection_manager is wrapper

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_open(self, double_wrapper: WrapperSqlConnectionManager) -> None:
        """Двойная обёртка запрещает open()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.open()

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_commit(self, double_wrapper: WrapperSqlConnectionManager) -> None:
        """Двойная обёртка запрещает commit()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.commit()

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_rollback(self, double_wrapper: WrapperSqlConnectionManager) -> None:
        """Двойная обёртка запрещает rollback()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.rollback()

    @pytest.mark.anyio
    async def test_double_wrapper_prohibits_begin(self, double_wrapper: WrapperSqlConnectionManager) -> None:
        """Двойная обёртка запрещает begin()."""
        with pytest.raises(TransactionProhibitedError):
            await double_wrapper.begin()

    @pytest.mark.anyio
    async def test_double_wrapper_delegates_execute_to_original(
        self, double_wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager,
    ) -> None:
        """execute() через двойную обёртку доходит до оригинального менеджера."""
        result = await double_wrapper.execute("SELECT 1")
        mock_manager.execute.assert_called_once_with("SELECT 1", None)
        assert result == "query_result"

    @pytest.mark.anyio
    async def test_triple_wrapper_works(
        self, double_wrapper: WrapperSqlConnectionManager, mock_manager: MockConnectionManager,
    ) -> None:
        """Тройная обёртка тоже работает — execute доходит до оригинала."""
        triple = WrapperSqlConnectionManager(double_wrapper)
        result = await triple.execute("SELECT 42")
        mock_manager.execute.assert_called_once_with("SELECT 42", None)
        assert result == "query_result"


# ======================================================================
# ТЕСТЫ: Интеграция с _wrap_connections
# ======================================================================

class TestWrapConnectionsIntegration:
    """
    Имитация логики ToolsBox._wrap_connections() — проверка что
    WrapperSqlConnectionManager корректно работает в реальном сценарии обёртки.
    """

    @staticmethod
    def _wrap_connections(connections: dict | None) -> dict | None:
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

    def test_wraps_mock_manager(self, mock_manager: MockConnectionManager) -> None:
        """Оборачивает MockConnectionManager в WrapperSqlConnectionManager."""
        connections = {"db": mock_manager}
        wrapped = self._wrap_connections(connections)

        assert "db" in wrapped
        assert isinstance(wrapped["db"], WrapperSqlConnectionManager)
        assert wrapped["db"]._connection_manager is mock_manager

    def test_wraps_wrapper_again(self, wrapper: WrapperSqlConnectionManager) -> None:
        """Повторная обёртка WrapperSqlConnectionManager работает."""
        connections = {"db": wrapper}
        wrapped = self._wrap_connections(connections)

        assert isinstance(wrapped["db"], WrapperSqlConnectionManager)
        assert wrapped["db"]._connection_manager is wrapper

    @pytest.mark.anyio
    async def test_wrapped_execute_works(self, mock_manager: MockConnectionManager) -> None:
        """execute() через обёрнутый менеджер работает."""
        connections = {"db": mock_manager}
        wrapped = self._wrap_connections(connections)

        result = await wrapped["db"].execute("INSERT INTO orders VALUES ($1)", (1,))
        mock_manager.execute.assert_called_once_with(
            "INSERT INTO orders VALUES ($1)", (1,)
        )
        assert result == "query_result"

    @pytest.mark.anyio
    async def test_wrapped_prohibits_transactions(self, mock_manager: MockConnectionManager) -> None:
        """Обёрнутый менеджер запрещает транзакции."""
        connections = {"db": mock_manager}
        wrapped = self._wrap_connections(connections)

        with pytest.raises(TransactionProhibitedError):
            await wrapped["db"].open()

        with pytest.raises(TransactionProhibitedError):
            await wrapped["db"].commit()

        with pytest.raises(TransactionProhibitedError):
            await wrapped["db"].rollback()

        with pytest.raises(TransactionProhibitedError):
            await wrapped["db"].begin()

    @pytest.mark.anyio
    async def test_double_wrap_execute_reaches_original(self, mock_manager: MockConnectionManager) -> None:
        """Двойная обёртка через _wrap_connections — execute доходит до оригинала."""
        # Первая обёртка (parent → child)
        wrapped_1 = self._wrap_connections({"db": mock_manager})
        # Вторая обёртка (child → grandchild)
        wrapped_2 = self._wrap_connections({"db": wrapped_1["db"]})

        result = await wrapped_2["db"].execute("SELECT 1")
        mock_manager.execute.assert_called_once_with("SELECT 1", None)
        assert result == "query_result"

    def test_none_connections_returns_none(self) -> None:
        """None connections → None."""
        assert self._wrap_connections(None) is None

    def test_empty_connections_returns_empty(self) -> None:
        """Пустой dict → пустой dict."""
        result = self._wrap_connections({})
        assert result == {}
