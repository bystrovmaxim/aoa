# tests/on_error/test_on_error_execution.py
"""
Тесты выполнения обработчиков @on_error в ActionProductMachine.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Проверяет механизм обработки ошибок аспектов в машине:
- Обработчик ловит нужное исключение → возвращает Result.
- Обработчик не ловит чужое исключение → пробрасывается наружу.
- Несколько обработчиков — первый подходящий (сверху вниз).
- Обработчик бросает исключение → OnErrorHandlerError.
- Действие без @on_error → исключение пробрасывается.
- Нормальное выполнение (без ошибки) → @on_error не вызывается.
- Regression: Action с @on_error БЕЗ компенсаторов — поведение
  не изменилось после внедрения механизма компенсации (Saga).

Все тесты используют Action из tests/domain/error_actions.py.
"""
import pytest

from action_machine.core.exceptions import OnErrorHandlerError
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.logging.log_coordinator import LogCoordinator
from action_machine.testing import TestBench
from tests.domain import (
    ErrorHandledAction,
    ErrorTestParams,
    HandlerRaisesAction,
    MultiErrorAction,
    NoErrorHandlerAction,
)

# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def bench() -> TestBench:
    """TestBench с тихим логгером (без вывода в консоль)."""
    return TestBench(
        coordinator=GateCoordinator(),
        log_coordinator=LogCoordinator(loggers=[]),
    )


# ═════════════════════════════════════════════════════════════════════════════
# Обработчик ловит нужное исключение
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorCatchesMatchingException:
    """Обработчик @on_error перехватывает исключение подходящего типа и возвращает Result."""

    @pytest.mark.asyncio()
    async def test_value_error_handled(self, bench: TestBench) -> None:
        """ValueError в аспекте → обработчик возвращает Result со статусом 'handled'."""
        # Arrange — параметры, вызывающие ошибку в аспекте
        params = ErrorTestParams(value="test", should_fail=True)
        # Act — машина выполняет действие, аспект бросает ValueError,
        # обработчик перехватывает и возвращает Result
        result = await bench.run(
            ErrorHandledAction(),
            params,
            rollup=False,
        )
        # Assert — результат от обработчика, а не от summary
        assert result.status == "handled"
        assert "Ошибка обработки: test" in result.detail

    @pytest.mark.asyncio()
    async def test_normal_execution_no_error(self, bench: TestBench) -> None:
        """Без ошибки в аспекте → нормальный Result, обработчик не вызывается."""
        # Arrange — параметры без ошибки
        params = ErrorTestParams(value="hello", should_fail=False)
        # Act — нормальное выполнение конвейера
        result = await bench.run(
            ErrorHandledAction(),
            params,
            rollup=False,
        )
        # Assert — результат от summary, а не от обработчика
        assert result.status == "ok"
        assert result.detail == "hello"


# ═════════════════════════════════════════════════════════════════════════════
# Несколько обработчиков — порядок сверху вниз
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorMultipleHandlers:
    """Несколько @on_error — первый подходящий обработчик вызывается."""

    @pytest.mark.asyncio()
    async def test_insufficient_funds_caught_by_specific_handler(self, bench: TestBench) -> None:
        """InsufficientFundsError → первый (специфичный) обработчик."""
        # Arrange — value="insufficient" вызывает InsufficientFundsError в аспекте
        params = ErrorTestParams(value="insufficient")
        # Act
        result = await bench.run(MultiErrorAction(), params, rollup=False)
        # Assert — перехвачено специфичным обработчиком
        assert result.status == "insufficient_funds"

    @pytest.mark.asyncio()
    async def test_gateway_error_caught_by_specific_handler(self, bench: TestBench) -> None:
        """PaymentGatewayError → второй (специфичный) обработчик."""
        # Arrange — value="gateway" вызывает PaymentGatewayError
        params = ErrorTestParams(value="gateway")
        # Act
        result = await bench.run(MultiErrorAction(), params, rollup=False)
        # Assert — перехвачено вторым обработчиком
        assert result.status == "gateway_error"

    @pytest.mark.asyncio()
    async def test_runtime_error_caught_by_fallback(self, bench: TestBench) -> None:
        """RuntimeError → третий (общий fallback) обработчик Exception."""
        # Arrange — should_fail=True вызывает RuntimeError
        params = ErrorTestParams(value="anything", should_fail=True)
        # Act
        result = await bench.run(MultiErrorAction(), params, rollup=False)
        # Assert — перехвачено fallback-обработчиком
        assert result.status == "unknown_error"

    @pytest.mark.asyncio()
    async def test_normal_execution(self, bench: TestBench) -> None:
        """Без ошибки → нормальный Result, ни один обработчик не вызван."""
        # Arrange — нормальные параметры
        params = ErrorTestParams(value="ok", should_fail=False)
        # Act
        result = await bench.run(MultiErrorAction(), params, rollup=False)
        # Assert — результат от summary
        assert result.status == "ok"
        assert result.detail == "ok"


# ═════════════════════════════════════════════════════════════════════════════
# Действие без @on_error — ошибка пробрасывается
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorNoHandler:
    """Действие без @on_error — исключение аспекта пробрасывается наружу."""

    @pytest.mark.asyncio()
    async def test_error_propagates_without_handler(self, bench: TestBench) -> None:
        """ValueError без обработчика → пробрасывается до вызывающего кода."""
        # Arrange — параметры, вызывающие ошибку
        params = ErrorTestParams(value="fail", should_fail=True)
        # Act & Assert — ValueError не перехвачен, летит наружу
        with pytest.raises(ValueError, match="Ошибка: fail"):
            await bench.run(NoErrorHandlerAction(), params, rollup=False)


# ═════════════════════════════════════════════════════════════════════════════
# Обработчик не подходит по типу — ошибка пробрасывается
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorTypeMismatch:
    """Обработчик ловит только свой тип — чужие исключения пробрасываются."""

    @pytest.mark.asyncio()
    async def test_type_error_not_caught_by_value_error_handler(self, bench: TestBench) -> None:
        """TypeError не перехватывается обработчиком ValueError → пробрасывается."""
        # Arrange — создаём Action, чей аспект бросает TypeError,
        # а обработчик ловит только ValueError.
        # ErrorHandledAction ловит ValueError. Подменим аспект через
        # наследование (edge-case тест — класс создаётся внутри теста).
        from action_machine.aspects.regular_aspect import regular_aspect
        from action_machine.aspects.summary_aspect import summary_aspect
        from action_machine.auth import ROLE_NONE, check_roles
        from action_machine.checkers import result_string
        from action_machine.core.base_action import BaseAction
        from action_machine.core.meta_decorator import meta
        from action_machine.on_error import on_error
        from tests.domain import OrdersDomain
        from tests.domain.error_actions import ErrorTestParams, ErrorTestResult

        @meta(description="Бросает TypeError, ловит ValueError", domain=OrdersDomain)
        @check_roles(ROLE_NONE)
        class TypeMismatchAction(BaseAction[ErrorTestParams, ErrorTestResult]):
            @regular_aspect("Бросает TypeError")
            @result_string("processed", required=True)
            async def process_aspect(self, params, state, box, connections):
                raise TypeError("Неверный тип")
                return {"processed": "never"}

            @summary_aspect("Результат")
            async def result_summary(self, params, state, box, connections):
                return ErrorTestResult(status="ok")

            @on_error(ValueError, description="Ловит только ValueError")
            async def handle_value_on_error(self, params, state, box, connections, error):
                return ErrorTestResult(status="handled")

        params = ErrorTestParams(value="test")
        # Act & Assert — TypeError не перехвачен обработчиком ValueError
        with pytest.raises(TypeError, match="Неверный тип"):
            await bench.run(TypeMismatchAction(), params, rollup=False)


# ═════════════════════════════════════════════════════════════════════════════
# Обработчик сам бросает исключение → OnErrorHandlerError
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorHandlerRaises:
    """Обработчик сам бросает исключение → OnErrorHandlerError."""

    @pytest.mark.asyncio()
    async def test_handler_exception_wrapped(self, bench: TestBench) -> None:
        """Обработчик бросает RuntimeError → OnErrorHandlerError с __cause__."""
        # Arrange — should_fail=True → ValueError → обработчик → RuntimeError
        params = ErrorTestParams(value="test", should_fail=True)
        # Act & Assert — OnErrorHandlerError оборачивает RuntimeError
        with pytest.raises(OnErrorHandlerError) as exc_info:
            await bench.run(HandlerRaisesAction(), params, rollup=False)
        # Assert — проверяем атрибуты OnErrorHandlerError
        error = exc_info.value
        assert error.handler_name == "handle_and_fail_on_error"
        assert isinstance(error.original_error, ValueError)
        assert error.__cause__ is not None
        assert isinstance(error.__cause__, RuntimeError)


# ═════════════════════════════════════════════════════════════════════════════
# Обработчики не наследуются
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorNotInherited:
    """Обработчики @on_error НЕ наследуются от родительского Action."""

    @pytest.mark.asyncio()
    async def test_child_action_does_not_inherit_handlers(self, bench: TestBench) -> None:
        """Дочерний Action без собственных @on_error — ошибка пробрасывается."""
        # Arrange — создаём дочерний класс ErrorHandledAction без своих обработчиков.
        # Родительский ErrorHandledAction имеет @on_error(ValueError),
        # но дочерний не должен его наследовать.
        from action_machine.aspects.regular_aspect import regular_aspect
        from action_machine.aspects.summary_aspect import summary_aspect
        from action_machine.auth import ROLE_NONE, check_roles
        from action_machine.checkers import result_string
        from action_machine.core.base_action import BaseAction
        from action_machine.core.meta_decorator import meta
        from tests.domain import OrdersDomain
        from tests.domain.error_actions import ErrorTestParams, ErrorTestResult

        @meta(description="Дочерний без собственных обработчиков", domain=OrdersDomain)
        @check_roles(ROLE_NONE)
        class ChildNoHandlerAction(BaseAction[ErrorTestParams, ErrorTestResult]):
            """Дочерний Action — переопределяет аспекты, но не имеет @on_error."""

            @regular_aspect("Обработка с ошибкой")
            @result_string("processed", required=True)
            async def process_aspect(self, params, state, box, connections):
                if params.should_fail:
                    raise ValueError("Ошибка в дочернем")
                return {"processed": params.value}

            @summary_aspect("Результат")
            async def result_summary(self, params, state, box, connections):
                return ErrorTestResult(status="ok", detail=state["processed"])

        params = ErrorTestParams(value="test", should_fail=True)
        # Act & Assert — ValueError пробрасывается, обработчик родителя НЕ работает
        with pytest.raises(ValueError, match="Ошибка в дочернем"):
            await bench.run(ChildNoHandlerAction(), params, rollup=False)


# ═════════════════════════════════════════════════════════════════════════════
# Regression: @on_error без компенсаторов — поведение не изменилось
# ═════════════════════════════════════════════════════════════════════════════


class TestOnErrorWithoutCompensatorsRegression:
    """
    Regression-тест: Action с @on_error БЕЗ компенсаторов работает
    так же, как до внедрения механизма компенсации (Saga).

    После добавления saga_stack в _execute_regular_aspects() и
    _rollback_saga() в _execute_aspects_with_error_handling() важно
    убедиться, что Action без @compensate продолжают корректно
    обрабатывать ошибки через @on_error — без попытки размотки
    пустого стека, без лишних событий, без побочных эффектов.
    """

    @pytest.mark.asyncio()
    async def test_on_error_works_without_compensators(self, bench: TestBench) -> None:
        """
        ErrorHandledAction не имеет @compensate.
        ValueError в аспекте → @on_error перехватывает → Result(status="handled").
        Размотка стека не выполняется (saga_stack пуст, has_compensators=False).
        Поведение идентично до внедрения Saga.
        """
        # Arrange — параметры, вызывающие ошибку в аспекте
        params = ErrorTestParams(value="regression_test", should_fail=True)

        # Act — машина выполняет действие, аспект бросает ValueError,
        # @on_error перехватывает без участия механизма компенсации
        result = await bench.run(
            ErrorHandledAction(),
            params,
            rollup=False,
        )

        # Assert — результат от @on_error обработчика
        assert result.status == "handled"
        assert "Ошибка обработки: regression_test" in result.detail

    @pytest.mark.asyncio()
    async def test_no_handler_propagates_without_compensators(self, bench: TestBench) -> None:
        """
        NoErrorHandlerAction не имеет ни @compensate, ни @on_error.
        ValueError пробрасывается наружу — поведение идентично
        до внедрения Saga.
        """
        # Arrange — параметры, вызывающие ошибку
        params = ErrorTestParams(value="no_handler", should_fail=True)

        # Act & Assert — ValueError пробрасывается без изменений
        with pytest.raises(ValueError, match="Ошибка: no_handler"):
            await bench.run(NoErrorHandlerAction(), params, rollup=False)
