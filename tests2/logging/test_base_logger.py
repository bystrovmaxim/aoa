# tests2/logging/test_base_logger.py
"""
Тесты абстрактного BaseLogger через RecordingLogger.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

BaseLogger — абстрактный базовый класс всех логгеров в системе. Определяет
фильтрацию сообщений по регулярным выражениям и передачу параметров в
конкретный метод write.

RecordingLogger — тестовый логгер-шпион, который накапливает все полученные
сообщения в списке records для последующей проверки.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

- Логгер без фильтров принимает все сообщения.
- Логгер с фильтрами пропускает только сообщения, проходящие regex.
- Фильтры проверяют scope, message и var-переменные.
- В write передаются все параметры, полученные handle.
- Логгер не модифицирует исходные словари var и state.
"""

from typing import Any

import pytest

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.logging.base_logger import BaseLogger
from action_machine.logging.log_scope import LogScope


class RecordingLogger(BaseLogger):
    """
    Тестовый логгер-шпион, записывающий все сообщения.

    Используется для проверки, какие сообщения прошли фильтрацию
    и с какими параметрами вызван write.
    """

    def __init__(self, filters: list[str] | None = None) -> None:
        super().__init__(filters=filters)
        self.records: list[dict[str, Any]] = []

    async def write(
        self,
        scope: LogScope,
        message: str,
        var: dict[str, Any],
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        indent: int,
    ) -> None:
        """Сохраняет вызов write в records."""
        self.records.append(
            {
                "scope": scope,
                "message": message,
                "var": var.copy(),
                "ctx": ctx,
                "state": state.to_dict(),
                "params": params,
                "indent": indent,
            }
        )


@pytest.fixture
def empty_context() -> Context:
    """Пустой контекст для тестов, где не нужны реальные данные."""
    return Context()


@pytest.fixture
def empty_state() -> BaseState:
    """Пустое состояние для тестов."""
    return BaseState()


@pytest.fixture
def empty_params() -> BaseParams:
    """Пустые параметры для тестов."""
    return BaseParams()


@pytest.fixture
def simple_scope() -> LogScope:
    """LogScope только с action для простых фильтров."""
    return LogScope(action="TestAction")


@pytest.fixture
def detailed_scope() -> LogScope:
    """LogScope с action, aspect и event для проверки dotpath в фильтрах."""
    return LogScope(action="TestAction", aspect="validate", event="before")


# ======================================================================
# ТЕСТЫ: Логгер без фильтров
# ======================================================================


class TestWithoutFilters:
    """Логгер без фильтров принимает все сообщения."""

    @pytest.mark.anyio
    async def test_passes_all_messages(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Логгер без фильтров (filters=None) принимает все сообщения,
        независимо от содержимого scope, message и var.
        """
        # Arrange — логгер без фильтров
        logger = RecordingLogger()

        # Act — отправляем сообщение
        await logger.handle(
            simple_scope, "test message", {"key": "value"},
            empty_context, empty_state, empty_params, indent=0,
        )

        # Assert — запись в records появилась
        assert len(logger.records) == 1
        assert logger.records[0]["message"] == "test message"

    @pytest.mark.anyio
    async def test_multiple_messages(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Последовательные вызовы handle накапливаются в records.
        """
        # Arrange
        logger = RecordingLogger()

        # Act — три сообщения подряд
        await logger.handle(simple_scope, "first", {}, empty_context, empty_state, empty_params, 0)
        await logger.handle(simple_scope, "second", {}, empty_context, empty_state, empty_params, 1)
        await logger.handle(simple_scope, "third", {}, empty_context, empty_state, empty_params, 2)

        # Assert — три записи
        assert len(logger.records) == 3
        assert [r["message"] for r in logger.records] == ["first", "second", "third"]
        assert [r["indent"] for r in logger.records] == [0, 1, 2]


# ======================================================================
# ТЕСТЫ: Логгер с фильтрами
# ======================================================================


class TestWithFilters:
    """Логгер с фильтрами пропускает только сообщения, проходящие regex."""

    @pytest.mark.anyio
    async def test_matching_filter_passes(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Если фильтр совпадает с filter_string, сообщение принимается.
        filter_string собирается из scope.as_dotpath(), message и var.
        """
        # Arrange — фильтр на TestAction в scope
        logger = RecordingLogger(filters=[r"TestAction"])
        # simple_scope.as_dotpath() = "TestAction"
        # filter_string = "TestAction " + message + " ..."

        # Act — scope содержит TestAction
        await logger.handle(
            simple_scope, "any", {}, empty_context, empty_state, empty_params, 0,
        )

        # Assert — запись создана
        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_non_matching_filter_rejects(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Если ни один фильтр не совпал, сообщение отклоняется.
        """
        # Arrange — фильтр на "PaymentAction", но scope.action = "TestAction"
        logger = RecordingLogger(filters=[r"PaymentAction"])

        # Act — scope не совпадает
        await logger.handle(
            simple_scope, "any", {}, empty_context, empty_state, empty_params, 0,
        )

        # Assert — записей нет
        assert len(logger.records) == 0

    @pytest.mark.anyio
    async def test_filter_matches_on_first_hit(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Достаточно совпадения хотя бы одного фильтра из списка.
        """
        # Arrange — список фильтров, второй подходит
        logger = RecordingLogger(
            filters=[r"NoMatch", r"TestAction", r"AnotherNoMatch"],
        )

        # Act — scope содержит TestAction
        await logger.handle(
            simple_scope, "any", {}, empty_context, empty_state, empty_params, 0,
        )

        # Assert — запись создана
        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_filter_checks_var(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Фильтр может проверять значения в var (преобразуются в строку key=value).
        """
        # Arrange — фильтр на наличие amount=1500 в var
        logger = RecordingLogger(filters=[r"amount=1500"])

        # Act — var содержит amount=1500
        await logger.handle(
            simple_scope, "payment", {"amount": 1500, "user": "john"},
            empty_context, empty_state, empty_params, 0,
        )

        # Assert — запись создана
        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_filter_checks_message_text(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Фильтр может проверять текст сообщения.
        """
        # Arrange — фильтр на слова ERROR или CRITICAL в тексте сообщения
        logger = RecordingLogger(filters=[r"ERROR|CRITICAL"])

        # Act — сообщение без ключевых слов → отклонено
        await logger.handle(
            simple_scope, "INFO: всё хорошо", {},
            empty_context, empty_state, empty_params, 0,
        )
        # Act — сообщение с ERROR → принято
        await logger.handle(
            simple_scope, "ERROR: что-то сломалось", {},
            empty_context, empty_state, empty_params, 0,
        )
        # Act — сообщение с CRITICAL → принято
        await logger.handle(
            simple_scope, "CRITICAL: система падает", {},
            empty_context, empty_state, empty_params, 0,
        )

        # Assert — два принятых сообщения
        assert len(logger.records) == 2
        assert logger.records[0]["message"] == "ERROR: что-то сломалось"
        assert logger.records[1]["message"] == "CRITICAL: система падает"

    @pytest.mark.anyio
    async def test_filter_checks_combined_string(
        self,
        detailed_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        filter_string объединяет scope.as_dotpath(), message и var в одну строку.
        Фильтр применяется к этой комбинированной строке.
        """
        # Arrange — фильтр на присутствие "TestAction.validate" (из scope) и amount=1500
        logger = RecordingLogger(filters=[r"TestAction\.validate.*amount=1500"])

        # Act — scope и var совпадают → принято
        await logger.handle(
            detailed_scope, "processing", {"amount": 1500},
            empty_context, empty_state, empty_params, 0,
        )

        # Act — scope совпадает, но amount=500 → не принято
        await logger.handle(
            detailed_scope, "processing", {"amount": 500},
            empty_context, empty_state, empty_params, 0,
        )

        # Act — scope не совпадает (действие другое), но amount=1500 → не принято
        other_scope = LogScope(action="OtherAction", aspect="validate")
        await logger.handle(
            other_scope, "processing", {"amount": 1500},
            empty_context, empty_state, empty_params, 0,
        )

        # Assert — только первое сообщение
        assert len(logger.records) == 1
        assert logger.records[0]["message"] == "processing"


# ======================================================================
# ТЕСТЫ: Передача параметров в write
# ======================================================================


class TestParameterPassing:
    """Логгер передаёт в write все параметры, полученные handle."""

    @pytest.mark.anyio
    async def test_passes_all_params(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        handle вызывает write с теми же параметрами (scope, message, var,
        ctx, state, params, indent), которые получил.
        """
        # Arrange — логгер без фильтров, чтобы гарантировать вызов write
        logger = RecordingLogger()
        state = BaseState({"total": 100, "processed": True})
        var = {"key": "value", "count": 42}
        indent = 3

        # Act — вызов handle со всеми параметрами
        await logger.handle(
            simple_scope, "test message", var,
            empty_context, state, empty_params, indent,
        )

        # Assert — в records сохранены все параметры
        record = logger.records[0]
        assert record["scope"] is simple_scope
        assert record["message"] == "test message"
        assert record["var"] == {"key": "value", "count": 42}
        assert record["ctx"] is empty_context
        assert record["state"] == {"total": 100, "processed": True}
        assert record["params"] is empty_params
        assert record["indent"] == indent

    @pytest.mark.anyio
    async def test_does_not_modify_original_var(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Логгер не изменяет переданный словарь var (не мутирует его).
        """
        # Arrange
        logger = RecordingLogger()
        original_var = {"key": "value"}
        var_copy = original_var.copy()

        # Act
        await logger.handle(
            simple_scope, "test", original_var,
            empty_context, empty_state, empty_params, 0,
        )

        # Assert — оригинал не изменился
        assert original_var == var_copy

    @pytest.mark.anyio
    async def test_does_not_modify_original_state(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Логгер не изменяет переданное состояние state.
        """
        # Arrange
        logger = RecordingLogger()
        original_state = BaseState({"total": 100})
        original_dict = original_state.to_dict()

        # Act
        await logger.handle(
            simple_scope, "test", {},
            empty_context, original_state, empty_params, 0,
        )

        # Assert — state не изменился
        assert original_state.to_dict() == original_dict


# ======================================================================
# ТЕСТЫ: Граничные случаи
# ======================================================================


class TestEdgeCases:
    """Обработка пустых значений и крайних случаев."""

    @pytest.mark.anyio
    async def test_empty_message(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Пустое сообщение допустимо, write получает пустую строку.
        """
        # Arrange
        logger = RecordingLogger()

        # Act
        await logger.handle(
            simple_scope, "", {},
            empty_context, empty_state, empty_params, 0,
        )

        # Assert
        assert len(logger.records) == 1
        assert logger.records[0]["message"] == ""

    @pytest.mark.anyio
    async def test_empty_var(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Пустой словарь var допустим.
        """
        # Arrange
        logger = RecordingLogger()

        # Act
        await logger.handle(
            simple_scope, "test", {},
            empty_context, empty_state, empty_params, 0,
        )

        # Assert
        assert len(logger.records) == 1
        assert logger.records[0]["var"] == {}

    @pytest.mark.anyio
    async def test_complex_var_values(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        var может содержать значения любых типов (списки, словари, None).
        """
        # Arrange
        logger = RecordingLogger()
        var = {
            "string": "text",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "none": None,
        }

        # Act
        await logger.handle(
            simple_scope, "complex", var,
            empty_context, empty_state, empty_params, 0,
        )

        # Assert
        assert len(logger.records) == 1
        assert logger.records[0]["var"] == var