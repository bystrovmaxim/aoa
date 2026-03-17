"""
Тесты LogCoordinator — координатора логирования.

Проверяем:
- Подстановку переменных из разных источников (var, context, params, state, scope)
- Обработку конструкций iif
- Рассылку сообщений по нескольким логерам
- Фильтрацию через логеры
- Обработку ошибок (несуществующие переменные, неизвестный namespace)
"""

import pytest

from action_machine.Core.Exceptions import LogTemplateError
from action_machine.Logging.log_coordinator import LogCoordinator
from action_machine.Logging.log_scope import LogScope
from tests.conftest import ParamsTest, RecordingLogger, make_context


class TestLogCoordinator:
    """Тесты координатора логирования."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Подстановка переменных из разных источников
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_emit_substitutes_var(self, recording_logger, scope, context_fixture, params):
        """emit подставляет переменные из var."""
        coordinator = LogCoordinator(loggers=[recording_logger])

        await coordinator.emit(
            message="Count is {%var.count}",
            var={"count": 42},
            scope=scope,
            ctx=context_fixture,
            state={},
            params=params,
            indent=0,
        )

        assert recording_logger.records[0]["message"] == "Count is 42"

    @pytest.mark.anyio
    async def test_emit_substitutes_context(self, recording_logger, scope, params):
        """emit подставляет переменные из context через resolve."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        ctx = make_context(user_id="agent_007")

        await coordinator.emit(
            message="User: {%context.user.user_id}",
            var={},
            scope=scope,
            ctx=ctx,
            state={},
            params=params,
            indent=0,
        )

        assert recording_logger.records[0]["message"] == "User: agent_007"

    @pytest.mark.anyio
    async def test_emit_substitutes_params(self, recording_logger, scope, context_fixture):
        """emit подставляет переменные из params через resolve."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        params = ParamsTest(amount=999.99)

        await coordinator.emit(
            message="Amount: {%params.amount}",
            var={},
            scope=scope,
            ctx=context_fixture,
            state={},
            params=params,
            indent=0,
        )

        assert recording_logger.records[0]["message"] == "Amount: 999.99"

    @pytest.mark.anyio
    async def test_emit_substitutes_state(self, recording_logger, scope, context_fixture, params):
        """emit подставляет переменные из state (dict)."""
        coordinator = LogCoordinator(loggers=[recording_logger])

        await coordinator.emit(
            message="Total: {%state.total}",
            var={},
            scope=scope,
            ctx=context_fixture,
            state={"total": 1500.0},
            params=params,
            indent=0,
        )

        assert recording_logger.records[0]["message"] == "Total: 1500.0"

    @pytest.mark.anyio
    async def test_emit_substitutes_scope(self, recording_logger, context_fixture, params):
        """emit подставляет переменные из scope."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        scope = LogScope(action="ProcessOrder", aspect="validate")

        await coordinator.emit(
            message="Action: {%scope.action}",
            var={},
            scope=scope,
            ctx=context_fixture,
            state={},
            params=params,
            indent=0,
        )

        assert recording_logger.records[0]["message"] == "Action: ProcessOrder"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Конструкции iif
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_emit_with_iif_simple(self, recording_logger, scope, context_fixture):
        """emit обрабатывает простой iif с единым синтаксисом {%...}."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        params = ParamsTest(amount=1500.0)

        await coordinator.emit(
            message="Risk: {iif({%params.amount} > 1000; 'HIGH'; 'LOW')}",
            var={},
            scope=scope,
            ctx=context_fixture,
            state={},
            params=params,
            indent=0,
        )

        assert recording_logger.records[0]["message"] == "Risk: HIGH"

    @pytest.mark.anyio
    async def test_emit_with_iif_nested(self, recording_logger, scope, context_fixture):
        """emit обрабатывает вложенные iif с единым синтаксисом."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        params = ParamsTest(amount=1500000.0)

        await coordinator.emit(
            message="Level: {iif({%params.amount} > 1000000; 'CRITICAL'; iif({%params.amount} > 100000; 'HIGH'; 'LOW'))}",
            var={},
            scope=scope,
            ctx=context_fixture,
            state={},
            params=params,
            indent=0,
        )

        assert recording_logger.records[0]["message"] == "Level: CRITICAL"

    @pytest.mark.anyio
    async def test_emit_with_iif_using_var(self, recording_logger, scope, context_fixture, params):
        """iif использует переменные из var."""
        coordinator = LogCoordinator(loggers=[recording_logger])

        await coordinator.emit(
            message="Result: {iif({%var.success} == True; 'OK'; 'FAIL')}",
            var={"success": True},
            scope=scope,
            ctx=context_fixture,
            state={},
            params=params,
            indent=0,
        )

        assert recording_logger.records[0]["message"] == "Result: OK"

    @pytest.mark.anyio
    async def test_emit_with_iif_using_state(self, recording_logger, scope, context_fixture, params):
        """iif использует переменные из state."""
        coordinator = LogCoordinator(loggers=[recording_logger])

        await coordinator.emit(
            message="Status: {iif({%state.processed} == True; 'DONE'; 'PENDING')}",
            var={},
            scope=scope,
            ctx=context_fixture,
            state={"processed": True},
            params=params,
            indent=0,
        )

        assert recording_logger.records[0]["message"] == "Status: DONE"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Рассылка по нескольким логерам
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_emit_broadcasts_to_all_loggers(self, scope, context_fixture, params):
        """emit рассылает сообщение всем зарегистрированным логерам."""
        logger1 = RecordingLogger()
        logger2 = RecordingLogger()
        coordinator = LogCoordinator(loggers=[logger1, logger2])

        await coordinator.emit(
            message="Broadcast",
            var={},
            scope=scope,
            ctx=context_fixture,
            state={},
            params=params,
            indent=0,
        )

        assert len(logger1.records) == 1
        assert len(logger2.records) == 1
        assert logger1.records[0]["message"] == "Broadcast"
        assert logger2.records[0]["message"] == "Broadcast"

    @pytest.mark.anyio
    async def test_emit_respects_logger_filters(self, scope, context_fixture, params):
        """emit вызывает все логеры, но каждый фильтрует самостоятельно."""
        logger_all = RecordingLogger()  # без фильтров — принимает всё
        logger_filtered = RecordingLogger(filters=[r"PaymentAction"])  # только Payment
        coordinator = LogCoordinator(loggers=[logger_all, logger_filtered])

        scope = LogScope(action="OrderAction")  # не PaymentAction

        await coordinator.emit(
            message="Order created",
            var={},
            scope=scope,
            ctx=context_fixture,
            state={},
            params=params,
            indent=0,
        )

        assert len(logger_all.records) == 1  # принял
        assert len(logger_filtered.records) == 0  # отклонил

    @pytest.mark.anyio
    async def test_add_logger(self, scope, context_fixture, params):
        """add_logger добавляет логер в координатор."""
        coordinator = LogCoordinator()
        logger = RecordingLogger()
        coordinator.add_logger(logger)

        await coordinator.emit(
            message="After add",
            var={},
            scope=scope,
            ctx=context_fixture,
            state={},
            params=params,
            indent=0,
        )

        assert len(logger.records) == 1

    @pytest.mark.anyio
    async def test_emit_without_loggers_does_nothing(self, scope, context_fixture, params):
        """emit без логеров не падает."""
        coordinator = LogCoordinator()

        # Не должно выбросить исключение
        await coordinator.emit(
            message="No loggers",
            var={},
            scope=scope,
            ctx=context_fixture,
            state={},
            params=params,
            indent=0,
        )

    # ------------------------------------------------------------------
    # ТЕСТЫ: Передача параметров
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_emit_passes_indent_to_loggers(self, recording_logger, scope, context_fixture, params):
        """emit передаёт indent в каждый логер."""
        coordinator = LogCoordinator(loggers=[recording_logger])

        await coordinator.emit(
            message="Indented",
            var={},
            scope=scope,
            ctx=context_fixture,
            state={},
            params=params,
            indent=5,
        )

        assert recording_logger.records[0]["indent"] == 5

    @pytest.mark.anyio
    async def test_emit_passes_scope_to_loggers(self, recording_logger, context_fixture, params):
        """emit передаёт scope в каждый логер."""
        coordinator = LogCoordinator(loggers=[recording_logger])
        test_scope = LogScope(action="TestAction", aspect="test")

        await coordinator.emit(
            message="Test",
            var={},
            scope=test_scope,
            ctx=context_fixture,
            state={},
            params=params,
            indent=0,
        )

        assert recording_logger.records[0]["scope"] is test_scope

    # ------------------------------------------------------------------
    # ТЕСТЫ: Вложенные структуры
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_emit_nested_state_dict(self, recording_logger, scope, context_fixture, params):
        """emit подставляет вложенные значения из state."""
        coordinator = LogCoordinator(loggers=[recording_logger])

        await coordinator.emit(
            message="Nested: {%state.order.id}",
            var={},
            scope=scope,
            ctx=context_fixture,
            state={"order": {"id": 42}},
            params=params,
            indent=0,
        )

        assert recording_logger.records[0]["message"] == "Nested: 42"

    @pytest.mark.anyio
    async def test_emit_nested_var_dict(self, recording_logger, scope, context_fixture, params):
        """emit подставляет вложенные значения из var."""
        coordinator = LogCoordinator(loggers=[recording_logger])

        await coordinator.emit(
            message="Var nested: {%var.data.value}",
            var={"data": {"value": "deep"}},
            scope=scope,
            ctx=context_fixture,
            state={},
            params=params,
            indent=0,
        )

        assert recording_logger.records[0]["message"] == "Var nested: deep"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Обработка ошибок
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_emit_missing_variable_raises(self, scope, context_fixture, params):
        """
        Обращение к несуществующей переменной выбрасывает LogTemplateError.
        """
        coordinator = LogCoordinator(loggers=[RecordingLogger()])

        with pytest.raises(LogTemplateError, match="не найдена"):
            await coordinator.emit(
                message="Missing: {%var.nonexistent}",
                var={},
                scope=scope,
                ctx=context_fixture,
                state={},
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_missing_variable_in_iif_raises(self, scope, context_fixture, params):
        """
        Обращение к несуществующей переменной внутри iif выбрасывает LogTemplateError.
        """
        coordinator = LogCoordinator(loggers=[RecordingLogger()])

        with pytest.raises(LogTemplateError, match="не найдена"):
            await coordinator.emit(
                message="Result: {iif({%var.missing} > 10; 'yes'; 'no')}",
                var={},
                scope=scope,
                ctx=context_fixture,
                state={},
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_unknown_namespace_raises(self, scope, context_fixture, params):
        """
        Неизвестный namespace в шаблоне выбрасывает LogTemplateError.
        """
        coordinator = LogCoordinator(loggers=[RecordingLogger()])

        with pytest.raises(LogTemplateError, match="Неизвестный namespace"):
            await coordinator.emit(
                message="Value: {%unknown.field}",
                var={},
                scope=scope,
                ctx=context_fixture,
                state={},
                params=params,
                indent=0,
            )

    @pytest.mark.anyio
    async def test_emit_invalid_iif_syntax_raises(self, scope, context_fixture, params):
        """
        Невалидный синтаксис iif (не 3 аргумента) выбрасывает LogTemplateError.
        """
        coordinator = LogCoordinator(loggers=[RecordingLogger()])

        with pytest.raises(LogTemplateError, match="iif ожидает 3 аргумента"):
            await coordinator.emit(
                message="Bad: {iif(1 > 0; 'only_two_args')}",
                var={},
                scope=scope,
                ctx=context_fixture,
                state={},
                params=params,
                indent=0,
            )
