# tests/domain/error_actions.py
"""
Action с обработчиками ошибок (@on_error) для тестирования Этапа 1.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит Action, демонстрирующие и тестирующие различные сценарии
обработки ошибок через @on_error:

- ErrorHandledAction — один обработчик, ловит ValueError.
- MultiErrorAction — несколько обработчиков (специфичный → общий).
- NoErrorHandlerAction — действие без @on_error (ошибки пробрасываются).
- HandlerRaisesAction — обработчик сам бросает исключение → OnErrorHandlerError.

═══════════════════════════════════════════════════════════════════════════════
ПОЛЬЗОВАТЕЛЬСКИЕ ИСКЛЮЧЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

- InsufficientFundsError — недостаточно средств на счёте.
- PaymentGatewayError — ошибка платёжного шлюза.

Оба наследуют Exception напрямую. Используются для тестирования
порядка обработчиков и перекрытия типов.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ В ТЕСТАХ
═══════════════════════════════════════════════════════════════════════════════

    from tests.domain.error_actions import (
        ErrorHandledAction,
        MultiErrorAction,
        NoErrorHandlerAction,
        HandlerRaisesAction,
        InsufficientFundsError,
        PaymentGatewayError,
    )
"""

from typing import Any

from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.checkers import result_string
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.base_state import BaseState
from action_machine.core.meta_decorator import meta
from action_machine.core.tools_box import ToolsBox
from action_machine.on_error import on_error
from action_machine.resource_managers.base_resource_manager import BaseResourceManager

from .domains import OrdersDomain

# ═════════════════════════════════════════════════════════════════════════════
# Пользовательские исключения
# ═════════════════════════════════════════════════════════════════════════════


class InsufficientFundsError(Exception):
    """Недостаточно средств на счёте."""
    pass


class PaymentGatewayError(Exception):
    """Ошибка платёжного шлюза."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Общие Params и Result для error-действий
# ═════════════════════════════════════════════════════════════════════════════


class ErrorTestParams(BaseParams):
    """Параметры для тестовых error-действий."""
    value: str = Field(description="Значение для обработки")
    should_fail: bool = Field(default=False, description="Если True — аспект бросит исключение")


class ErrorTestResult(BaseResult):
    """Результат тестовых error-действий."""
    status: str = Field(description="Статус выполнения")
    detail: str = Field(default="", description="Детали результата")


# ═════════════════════════════════════════════════════════════════════════════
# ErrorHandledAction — один обработчик ValueError
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Действие с одним обработчиком ValueError", domain=OrdersDomain)
@check_roles(ROLE_NONE)
class ErrorHandledAction(BaseAction[ErrorTestParams, ErrorTestResult]):
    """
    Действие с одним @on_error обработчиком для ValueError.

    Если should_fail=True, regular-аспект бросает ValueError.
    Обработчик handle_validation_on_error перехватывает ValueError
    и возвращает Result со статусом "handled".

    Сценарии тестирования:
    - should_fail=False → нормальный Result(status="ok").
    - should_fail=True → обработчик → Result(status="handled").
    """

    @regular_aspect("Обработка значения")
    @result_string("processed", required=True)
    async def process_aspect(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        if params.should_fail:
            raise ValueError(f"Ошибка обработки: {params.value}")
        return {"processed": params.value}

    @summary_aspect("Формирование результата")
    async def build_result_summary(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> ErrorTestResult:
        return ErrorTestResult(status="ok", detail=state["processed"])

    @on_error(ValueError, description="Обработка ошибки валидации")
    async def handle_validation_on_error(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> ErrorTestResult:
        return ErrorTestResult(status="handled", detail=str(error))


# ═════════════════════════════════════════════════════════════════════════════
# MultiErrorAction — несколько обработчиков (специфичный → общий)
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Действие с несколькими обработчиками ошибок", domain=OrdersDomain)
@check_roles(ROLE_NONE)
class MultiErrorAction(BaseAction[ErrorTestParams, ErrorTestResult]):
    """
    Действие с тремя @on_error обработчиками в порядке от специфичного к общему.

    Порядок обработчиков:
    1. InsufficientFundsError — специфичный.
    2. PaymentGatewayError — специфичный.
    3. Exception — общий fallback.

    Сценарии тестирования:
    - InsufficientFundsError → обработчик 1 → status="insufficient_funds".
    - PaymentGatewayError → обработчик 2 → status="gateway_error".
    - RuntimeError (или любой Exception) → обработчик 3 → status="unknown_error".
    - Нет ошибки → нормальный Result(status="ok").
    """

    @regular_aspect("Выполнение операции")
    @result_string("processed", required=True)
    async def execute_aspect(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        if params.value == "insufficient":
            raise InsufficientFundsError("Недостаточно средств")
        if params.value == "gateway":
            raise PaymentGatewayError("Шлюз недоступен")
        if params.should_fail:
            raise RuntimeError("Непредвиденная ошибка")
        return {"processed": params.value}

    @summary_aspect("Формирование результата")
    async def build_result_summary(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> ErrorTestResult:
        return ErrorTestResult(status="ok", detail=state["processed"])

    @on_error(InsufficientFundsError, description="Недостаточно средств")
    async def insufficient_funds_on_error(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> ErrorTestResult:
        return ErrorTestResult(status="insufficient_funds", detail=str(error))

    @on_error(PaymentGatewayError, description="Ошибка платёжного шлюза")
    async def gateway_on_error(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> ErrorTestResult:
        return ErrorTestResult(status="gateway_error", detail=str(error))

    @on_error(Exception, description="Непредвиденная ошибка")
    async def fallback_on_error(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> ErrorTestResult:
        return ErrorTestResult(status="unknown_error", detail=str(error))


# ═════════════════════════════════════════════════════════════════════════════
# NoErrorHandlerAction — без @on_error (ошибки пробрасываются)
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Действие без обработчиков ошибок", domain=OrdersDomain)
@check_roles(ROLE_NONE)
class NoErrorHandlerAction(BaseAction[ErrorTestParams, ErrorTestResult]):
    """
    Действие без @on_error — ошибки аспектов пробрасываются наружу.

    Сценарии тестирования:
    - should_fail=True → ValueError пробрасывается до вызывающего кода.
    - should_fail=False → нормальный Result(status="ok").
    """

    @regular_aspect("Обработка значения")
    @result_string("processed", required=True)
    async def process_aspect(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        if params.should_fail:
            raise ValueError(f"Ошибка: {params.value}")
        return {"processed": params.value}

    @summary_aspect("Формирование результата")
    async def build_result_summary(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> ErrorTestResult:
        return ErrorTestResult(status="ok", detail=state["processed"])


# ═════════════════════════════════════════════════════════════════════════════
# HandlerRaisesAction — обработчик сам бросает исключение
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Действие с обработчиком, который сам бросает исключение", domain=OrdersDomain)
@check_roles(ROLE_NONE)
class HandlerRaisesAction(BaseAction[ErrorTestParams, ErrorTestResult]):
    """
    Действие, чей @on_error обработчик сам бросает исключение.

    Аспект бросает ValueError. Обработчик handle_and_fail_on_error
    перехватывает ValueError, но сам бросает RuntimeError.
    Машина оборачивает RuntimeError в OnErrorHandlerError.

    Сценарии тестирования:
    - should_fail=True → ValueError → обработчик → RuntimeError →
      OnErrorHandlerError с __cause__=RuntimeError
      и original_error=ValueError.
    """

    @regular_aspect("Обработка значения")
    @result_string("processed", required=True)
    async def process_aspect(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> dict[str, Any]:
        if params.should_fail:
            raise ValueError(f"Ошибка: {params.value}")
        return {"processed": params.value}

    @summary_aspect("Формирование результата")
    async def build_result_summary(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
    ) -> ErrorTestResult:
        return ErrorTestResult(status="ok", detail=state["processed"])

    @on_error(ValueError, description="Обработчик, который сам падает")
    async def handle_and_fail_on_error(
        self,
        params: ErrorTestParams,
        state: BaseState,
        box: ToolsBox,
        connections: dict[str, BaseResourceManager],
        error: Exception,
    ) -> ErrorTestResult:
        raise RuntimeError(f"Ошибка в обработчике: {error}")
