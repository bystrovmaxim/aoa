# tests/logging/test_log_coordinator.py
"""
Тесты LogCoordinator — центральной шины логирования.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

LogCoordinator — единственная шина, через которую проходят все сообщения
логирования. Он принимает сообщение, подставляет переменные из разных
namespace (var, context, params, state, scope) через VariableSubstitutor,
вычисляет iif-конструкции, а затем рассылает результат всем зарегистрированным
логгерам.

Координатор вызывает logger.handle() для каждого логгера. Метод handle()
определён в BaseLogger и выполняет двухфазный протокол:
1. Фильтрация — match_filters() проверяет сообщение по регулярным выражениям.
2. Запись — write() выполняет фактический вывод (только если фильтрация прошла).

RecordingLogger в этом модуле наследует BaseLogger и использует его метод
handle() без переопределения. Это гарантирует, что фильтрация работает
так же, как в реальных логгерах.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Подстановка переменных:
    - Из var: {%var.key}
    - Из context: {%context.user.user_id}
    - Из params: {%params.amount}
    - Из state: {%state.total}
    - Из scope: {%scope.action}

iif-конструкции:
    - Простые условия внутри сообщения.
    - Вложенные iif.
    - Использование переменных внутри iif.

Рассылка логгерам:
    - Сообщение доставляется всем зарегистрированным логгерам.
    - Каждый логгер фильтрует независимо через BaseLogger.handle().
    - Пустой список логгеров не вызывает ошибок.

Параметры:
    - indent передаётся логгерам.
    - scope передаётся логгерам.

Ошибки:
    - Отсутствующая переменная → LogTemplateError.
    - Неизвестный namespace → LogTemplateError.
    - Невалидный iif → LogTemplateError.
    - Имя с подчёркиванием → LogTemplateError.
"""

from typing import Any

import pytest

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.core.exceptions import LogTemplateError
from action_machine.logging.base_logger import BaseLogger
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.logging.log_scope import LogScope


class RecordingLogger(BaseLogger):
    """
    Логгер-шпион, наследующий BaseLogger для корректной фильтрации.

    Наследует BaseLogger.handle(), который выполняет двухфазный протокол:
    1. match_filters() — проверяет сообщение по regex-фильтрам.
    2. write() — вызывается только если фильтрация прошла.

    Метод write() записывает все полученные данные в список records
    для последующей проверки в тестах. Это гарантирует, что фильтрация
    работает идентично реальным логгерам (ConsoleLogger и др.).
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
        self.records.append({
            "scope": scope,
            "message": message,
            "var": var.copy(),
            "ctx": ctx,
            "state": state.to_dict(),
            "params": params,
            "indent": indent,
        })


@pytest.fixture
def empty_context() -> Context:
    return Context()


@pytest.fixture
def empty_state() -> BaseState:
    return BaseState()


@pytest.fixture
def empty_params() -> BaseParams:
    return BaseParams()


@pytest.fixture
def simple_scope() -> LogScope:
    return LogScope(action="TestAction")


@pytest.fixture
def detailed_scope() -> LogScope:
    return LogScope(action="TestAction", aspect="validate")


# ======================================================================
# ТЕСТЫ: Подстановка переменных из разных источников
# ======================================================================


class TestVariableSubstitution:
    """LogCoordinator подставляет переменные из var, context, params, state, scope."""

    @pytest.mark.anyio
    async def test_substitutes_var(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        {%var.count} заменяется на значение из словаря var.
        """
        # Arrange
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        var = {"count": 42}

        # Act
        await coordinator.emit(
            message="Count is {%var.count}",
            var=var,
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Count is 42"

    @pytest.mark.anyio
    async def test_substitutes_context(
        self,
        simple_scope: LogScope,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        {%context.user.user_id} подставляется через resolve из Context.
        """
        # Arrange
        from action_machine.context.user_info import UserInfo
        ctx = Context(user=UserInfo(user_id="agent_007"))
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="User: {%context.user.user_id}",
            var={},
            scope=simple_scope,
            ctx=ctx,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "User: agent_007"

    @pytest.mark.anyio
    async def test_substitutes_params(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
    ) -> None:
        """
        {%params.amount} подставляется из pydantic-модели параметров.
        """
        # Arrange
        from pydantic import Field
        class TestParams(BaseParams):
            amount: float = Field(default=999.99, description="Сумма")

        params = TestParams(amount=999.99)
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="Amount: {%params.amount}",
            var={},
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Amount: 999.99"

    @pytest.mark.anyio
    async def test_substitutes_state(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_params: BaseParams,
    ) -> None:
        """
        {%state.total} подставляется из BaseState.
        """
        # Arrange
        state = BaseState(total=1500.0)
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="Total: {%state.total}",
            var={},
            scope=simple_scope,
            ctx=empty_context,
            state=state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Total: 1500.0"

    @pytest.mark.anyio
    async def test_substitutes_scope(
        self,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        {%scope.action} подставляется из LogScope.
        """
        # Arrange
        scope = LogScope(action="ProcessOrder", aspect="validate")
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="Action: {%scope.action}",
            var={},
            scope=scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Action: ProcessOrder"


# ======================================================================
# ТЕСТЫ: iif-конструкции
# ======================================================================


class TestIifConstructs:
    """LogCoordinator обрабатывает конструкции {iif(...)}."""

    @pytest.mark.anyio
    async def test_simple_iif(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        {iif(условие; ветка_истина; ветка_ложь)} вычисляется и подставляется.
        """
        # Arrange
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        var = {"amount": 1500.0}

        # Act — iif с {%var.amount} внутри
        await coordinator.emit(
            message="Risk: {iif({%var.amount} > 1000; 'HIGH'; 'LOW')}",
            var=var,
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Risk: HIGH"

    @pytest.mark.anyio
    async def test_nested_iif(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Вложенные iif корректно вычисляются.
        """
        # Arrange
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        var = {"amount": 1500000.0}

        # Act
        await coordinator.emit(
            message="Level: {iif({%var.amount} > 1000000; 'CRITICAL'; iif({%var.amount} > 100000; 'HIGH'; 'LOW'))}",
            var=var,
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Level: CRITICAL"

    @pytest.mark.anyio
    async def test_iif_with_state(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_params: BaseParams,
    ) -> None:
        """
        iif может использовать переменные из state.
        """
        # Arrange
        state = BaseState(processed=True)
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="Status: {iif({%state.processed} == True; 'DONE'; 'PENDING')}",
            var={},
            scope=simple_scope,
            ctx=empty_context,
            state=state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Status: DONE"


# ======================================================================
# ТЕСТЫ: Рассылка логгерам
# ======================================================================


class TestBroadcast:
    """Сообщение рассылается всем зарегистрированным логгерам."""

    @pytest.mark.anyio
    async def test_broadcast_to_all_loggers(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Каждый логгер получает сообщение (после своей фильтрации).
        """
        # Arrange — два логгера без фильтров
        logger1 = RecordingLogger()
        logger2 = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger1, logger2])

        # Act
        await coordinator.emit(
            message="Broadcast",
            var={},
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert — оба получили сообщение
        assert len(logger1.records) == 1
        assert len(logger2.records) == 1
        assert logger1.records[0]["message"] == "Broadcast"
        assert logger2.records[0]["message"] == "Broadcast"

    @pytest.mark.anyio
    async def test_respects_logger_filters(
        self,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Каждый логгер фильтрует сообщение независимо через BaseLogger.handle().

        all_logger (без фильтров) принимает все сообщения.
        filtered_logger (фильтр на "PaymentAction") отклоняет сообщение
        с scope.action="OrderAction", потому что filter_string не содержит
        "PaymentAction".
        """
        # Arrange — логгер без фильтров и логгер с фильтром на PaymentAction
        all_logger = RecordingLogger()
        filtered_logger = RecordingLogger(filters=[r"PaymentAction"])
        coordinator = LogCoordinator(loggers=[all_logger, filtered_logger])
        scope = LogScope(action="OrderAction")

        # Act — отправляем сообщение от OrderAction (не PaymentAction)
        await coordinator.emit(
            message="Order created",
            var={},
            scope=scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert — all_logger получил, filtered_logger отклонил
        assert len(all_logger.records) == 1
        assert len(filtered_logger.records) == 0

    @pytest.mark.anyio
    async def test_add_logger(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Логгер можно добавить после создания координатора.
        """
        # Arrange
        coordinator = LogCoordinator()
        logger = RecordingLogger()

        # Act
        coordinator.add_logger(logger)
        await coordinator.emit(
            message="After add",
            var={},
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_emit_without_loggers(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        emit без логгеров не вызывает ошибок.
        """
        # Arrange
        coordinator = LogCoordinator()

        # Act — не должно быть исключений
        await coordinator.emit(
            message="No loggers",
            var={},
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )


# ======================================================================
# ТЕСТЫ: Передача параметров логгерам
# ======================================================================


class TestParameterPassing:
    """LogCoordinator передаёт параметры логгерам."""

    @pytest.mark.anyio
    async def test_passes_indent(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        indent передаётся каждому логгеру без изменений.
        """
        # Arrange
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="Indented",
            var={},
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=5,
        )

        # Assert
        assert logger.records[0]["indent"] == 5

    @pytest.mark.anyio
    async def test_passes_scope(
        self,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        scope передаётся логгерам.
        """
        # Arrange
        scope = LogScope(action="MyAction", aspect="test")
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="Test",
            var={},
            scope=scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["scope"] is scope


# ======================================================================
# ТЕСТЫ: Вложенные структуры
# ======================================================================


class TestNestedStructures:
    """Подстановка вложенных значений (dict внутри state, var и т.д.)."""

    @pytest.mark.anyio
    async def test_nested_state(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_params: BaseParams,
    ) -> None:
        """
        Доступ к вложенным ключам state через точку: {%state.order.id}.
        """
        # Arrange
        state = BaseState(order={"id": 42})
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="Order ID: {%state.order.id}",
            var={},
            scope=simple_scope,
            ctx=empty_context,
            state=state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Order ID: 42"

    @pytest.mark.anyio
    async def test_nested_var(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Доступ к вложенным ключам var: {%var.data.value}.
        """
        # Arrange
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        var = {"data": {"value": "deep"}}

        # Act
        await coordinator.emit(
            message="Value: {%var.data.value}",
            var=var,
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        # Assert
        assert logger.records[0]["message"] == "Value: deep"


# ======================================================================
# ТЕСТЫ: Обработка ошибок
# ======================================================================


class TestErrorHandling:
    """LogCoordinator пробрасывает LogTemplateError при ошибках в шаблоне."""

    @pytest.mark.anyio
    async def test_missing_variable_raises(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Обращение к несуществующей переменной → LogTemplateError.
        """
        # Arrange
        coordinator = LogCoordinator(loggers=[])

        # Act & Assert
        with pytest.raises(LogTemplateError, match="not found"):
            await coordinator.emit(
                message="Missing: {%var.nonexistent}",
                var={},
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_unknown_namespace_raises(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Неизвестный namespace в шаблоне → LogTemplateError.
        """
        # Arrange
        coordinator = LogCoordinator(loggers=[])

        # Act & Assert
        with pytest.raises(LogTemplateError, match="Unknown namespace"):
            await coordinator.emit(
                message="Value: {%unknown.field}",
                var={},
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_underscore_name_raises(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Доступ к имени, начинающемуся с подчёркивания → LogTemplateError.
        """
        # Arrange
        coordinator = LogCoordinator(loggers=[])
        var = {"_secret": "value"}

        # Act & Assert
        with pytest.raises(LogTemplateError, match="Access to name starting with underscore is forbidden"):
            await coordinator.emit(
                message="Secret: {%var._secret}",
                var=var,
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_missing_variable_in_iif_raises(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        Переменная внутри iif не найдена → LogTemplateError.
        """
        # Arrange
        coordinator = LogCoordinator(loggers=[])

        # Act & Assert
        with pytest.raises(LogTemplateError, match="not found"):
            await coordinator.emit(
                message="Result: {iif({%var.missing} > 10; 'yes'; 'no')}",
                var={},
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_invalid_iif_syntax_raises(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """
        iif с неверным количеством аргументов → LogTemplateError.
        """
        # Arrange
        coordinator = LogCoordinator(loggers=[])

        # Act & Assert
        with pytest.raises(LogTemplateError, match="iif expects 3 arguments"):
            await coordinator.emit(
                message="Bad: {iif(1 > 0; 'only_two_args')}",
                var={},
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )
