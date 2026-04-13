# tests/intents/logging/test_log_coordinator.py
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
1. Фильтрация — match_filters() и подписки subscribe().
2. Запись — write() выполняет фактический вывод (только если фильтрация прошла).

RecordingLogger наследует BaseLogger.handle() без переопределения.

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

Изоляция логгеров:
    - Исключение в ``handle`` одного ``BaseLogger`` не прерывает ``emit`` и не
      лишает остальных логгеров вызова; сбой пишется в stdlib ``logging``
      (см. README и ``log_coordinator``).
"""

import logging
from typing import Any

import pytest

from action_machine.intents.context.context import Context
from action_machine.intents.logging.base_logger import BaseLogger
from action_machine.intents.logging.channel import Channel, channel_mask_label
from action_machine.intents.logging.level import Level, level_label
from action_machine.intents.logging.log_coordinator import LogCoordinator
from action_machine.intents.logging.log_scope import LogScope
from action_machine.intents.logging.log_var_payloads import LogChannelPayload, LogLevelPayload
from action_machine.model.base_params import BaseParams
from action_machine.model.base_state import BaseState
from action_machine.model.exceptions import LogTemplateError


def _valid_emit_var(**extra: Any) -> dict[str, Any]:
    li = Level.info
    cd = Channel.debug
    return {
        "level": LogLevelPayload(mask=li, name=level_label(li)),
        "channels": LogChannelPayload(mask=cd, names=channel_mask_label(cd)),
        "domain": None,
        "domain_name": None,
        **extra,
    }


class RecordingLogger(BaseLogger):
    """Шпион: write складывает вызовы в records (как ConsoleLogger по протоколу)."""

    def __init__(self) -> None:
        super().__init__()
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


class FailingLogger(BaseLogger):
    """Падает в ``write`` — для проверки изоляции при fan-out."""

    def __init__(self) -> None:
        super().__init__()
        self.write_calls = 0

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
        self.write_calls += 1
        raise RuntimeError("intentional sink failure")


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
        var = _valid_emit_var(count=42)

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
        from action_machine.intents.context.user_info import UserInfo
        ctx = Context(user=UserInfo(user_id="agent_007"))
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])

        # Act
        await coordinator.emit(
            message="User: {%context.user.user_id}",
            var=_valid_emit_var(),
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
            var=_valid_emit_var(),
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
            var=_valid_emit_var(),
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
            var=_valid_emit_var(),
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
        var = _valid_emit_var(amount=1500.0)

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
        var = _valid_emit_var(amount=1500000.0)

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
            var=_valid_emit_var(),
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
            var=_valid_emit_var(),
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
        Логгеры независимо решают, писать ли сообщение: подписки у второго
        логгера не совпадают с каналом в var (debug vs business).
        """
        all_logger = RecordingLogger()
        filtered_logger = RecordingLogger()
        filtered_logger.subscribe("only_business", channels=Channel.business)
        coordinator = LogCoordinator(loggers=[all_logger, filtered_logger])
        scope = LogScope(action="OrderAction")

        await coordinator.emit(
            message="Order created",
            var=_valid_emit_var(),
            scope=scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

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
            var=_valid_emit_var(),
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
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )


# ======================================================================
# ТЕСТЫ: изоляция ошибок в handle (B-2 / best-effort logging)
# ======================================================================


_COORDINATOR_FAILURE_LOGGER = "action_machine.intents.logging.log_coordinator"


class TestLoggerHandleFailureIsolation:
    """Сбой одного BaseLogger не рвёт emit и не блокирует остальные синги."""

    @pytest.mark.anyio
    async def test_second_logger_receives_message_when_first_raises(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        failing = FailingLogger()
        recording = RecordingLogger()
        coordinator = LogCoordinator(loggers=[failing, recording])

        await coordinator.emit(
            message="Fan-out",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        assert failing.write_calls == 1
        assert len(recording.records) == 1
        assert recording.records[0]["message"] == "Fan-out"

    @pytest.mark.anyio
    async def test_emit_completes_when_all_loggers_fail(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        a = FailingLogger()
        b = FailingLogger()
        coordinator = LogCoordinator(loggers=[a, b])

        await coordinator.emit(
            message="All bad",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )

        assert a.write_calls == 1
        assert b.write_calls == 1

    @pytest.mark.anyio
    async def test_failed_logger_emits_stdlib_error_record(
        self,
        caplog: pytest.LogCaptureFixture,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        """Нет второго LogCoordinator — сбой сингa уходит в stdlib logging."""
        coordinator = LogCoordinator(loggers=[FailingLogger()])
        with caplog.at_level(logging.ERROR, logger=_COORDINATOR_FAILURE_LOGGER):
            await coordinator.emit(
                message="Sink down",
                var=_valid_emit_var(),
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )

        assert any(
            "LogCoordinator" in r.getMessage() and "raised during emit" in r.getMessage()
            for r in caplog.records
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
            var=_valid_emit_var(),
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
            var=_valid_emit_var(),
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
            var=_valid_emit_var(),
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
        var = _valid_emit_var(data={"value": "deep"})

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

    @pytest.mark.anyio
    async def test_substitutes_level_name_and_channel_names(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        logger = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger])
        await coordinator.emit(
            message="{%var.level.name}|{%var.channels.names}",
            var=_valid_emit_var(),
            scope=simple_scope,
            ctx=empty_context,
            state=empty_state,
            params=empty_params,
            indent=0,
        )
        assert logger.records[0]["message"] == "INFO|debug"


# ======================================================================
# ТЕСТЫ: Обработка ошибок
# ======================================================================


class TestErrorHandling:
    """LogCoordinator пробрасывает LogTemplateError при ошибках в шаблоне."""

    @pytest.mark.anyio
    async def test_emit_requires_level_and_channels(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        coordinator = LogCoordinator(loggers=[])
        with pytest.raises(ValueError, match="var must contain"):
            await coordinator.emit(
                message="x",
                var={"channels": LogChannelPayload(
                    mask=Channel.debug, names=channel_mask_label(Channel.debug),
                )},
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_rejects_raw_level_not_payload(
        self,
        simple_scope: LogScope,
        empty_context: Context,
        empty_state: BaseState,
        empty_params: BaseParams,
    ) -> None:
        coordinator = LogCoordinator(loggers=[])
        bad = {**_valid_emit_var(), "level": Level.info}
        with pytest.raises(TypeError, match="LogLevelPayload"):
            await coordinator.emit(
                message="x",
                var=bad,
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )

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
                var=_valid_emit_var(),
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
                var=_valid_emit_var(),
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
        var = {**_valid_emit_var(), "_secret": "value"}

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
                var=_valid_emit_var(),
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
                var=_valid_emit_var(),
                scope=simple_scope,
                ctx=empty_context,
                state=empty_state,
                params=empty_params,
                indent=0,
            )
