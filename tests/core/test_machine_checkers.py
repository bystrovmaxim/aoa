# tests/core/test_machine_checkers.py
"""
Тесты валидации результатов аспектов чекерами в ActionProductMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

После выполнения каждого regular-аспекта машина проверяет возвращённый dict
через чекеры, привязанные к этому аспекту в ClassMetadata. Чекеры объявляются
декораторами (@result_string, @result_int, @result_float и др.) на методе
аспекта. MetadataBuilder собирает их в ClassMetadata.checkers.

ActionProductMachine._execute_regular_aspects() применяет три правила:

1. Если аспект вернул НЕ dict → TypeError.

2. Если аспект НЕ имеет чекеров и вернул НЕПУСТОЙ dict → ValidationFieldError.

3. Если аспект имеет чекеры:
   a. Лишние поля (не объявленные в чекерах) → ValidationFieldError.
   b. Каждый чекер проверяет тип и constraints своего поля.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Правило 1 — не dict:
    - Regular-аспект возвращает строку → TypeError.

Правило 2 — нет чекеров:
    - Regular-аспект без чекеров возвращает {} → OK.
    - Regular-аспект без чекеров возвращает {"key": "val"} → ValidationFieldError.

Правило 3 — чекеры:
    - Все поля объявлены, все проходят проверку → OK.
    - Лишнее поле (не объявлено в чекерах) → ValidationFieldError.
    - Поле не проходит проверку типа (int вместо str) → ValidationFieldError.

Интеграция с доменной моделью:
    - SimpleAction: validate_name_aspect с result_string → OK.
    - FullAction: process_payment_aspect (result_string) + calc_total_aspect (result_float) → OK.
"""

from unittest.mock import AsyncMock

import pytest

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.checkers import result_float, result_string
from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.action_product_machine import ActionProductMachine
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.exceptions import ValidationFieldError
from action_machine.core.meta_decorator import meta
from action_machine.logging.log_coordinator import LogCoordinator
from tests.domain_model import FullAction, NotificationService, PaymentService, SimpleAction, TestDbManager

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные действия для edge-case тестов
# ═════════════════════════════════════════════════════════════════════════════


class _MockParams(BaseParams):
    """Пустые параметры для edge-case действий."""
    pass


class _MockResult(BaseResult):
    """Пустой результат для edge-case действий."""
    pass


@meta(description="Аспект возвращает не dict — TypeError")
@check_roles(ROLE_NONE)
class _ActionBadReturnAction(BaseAction[_MockParams, _MockResult]):
    """Regular-аспект возвращает строку вместо dict."""

    @regular_aspect("bad")
    async def bad_aspect(self, params, state, box, connections):
        return "not a dict"

    @summary_aspect("summary")
    async def build_summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Нет чекеров, но вернул непустой dict")
@check_roles(ROLE_NONE)
class _ActionNoCheckersNonEmptyReturnAction(BaseAction[_MockParams, _MockResult]):
    """Regular-аспект без чекеров возвращает данные — ValidationFieldError."""

    @regular_aspect("no checkers")
    async def no_checkers_aspect(self, params, state, box, connections):
        return {"field": "value"}

    @summary_aspect("summary")
    async def build_summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Нет чекеров, вернул пустой dict")
@check_roles(ROLE_NONE)
class _ActionNoCheckersEmptyReturnAction(BaseAction[_MockParams, _MockResult]):
    """Regular-аспект без чекеров возвращает {} — OK."""

    @regular_aspect("no checkers empty")
    async def empty_aspect(self, params, state, box, connections):
        return {}

    @summary_aspect("summary")
    async def build_summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Чекер на одно поле, но возвращает лишнее")
@check_roles(ROLE_NONE)
class _ActionExtraFieldAction(BaseAction[_MockParams, _MockResult]):
    """Аспект с чекером на field, но возвращает ещё extra."""

    @regular_aspect("extra field")
    @result_string("field", required=True)
    async def extra_field_aspect(self, params, state, box, connections):
        return {"field": "ok", "extra": "forbidden"}

    @summary_aspect("summary")
    async def build_summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Чекер ожидает строку, аспект возвращает int")
@check_roles(ROLE_NONE)
class _ActionWrongTypeAction(BaseAction[_MockParams, _MockResult]):
    """Аспект возвращает int в поле, где ожидается строка."""

    @regular_aspect("wrong type")
    @result_string("name", required=True)
    async def wrong_type_aspect(self, params, state, box, connections):
        return {"name": 42}  # int вместо str

    @summary_aspect("summary")
    async def build_summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Два чекера, оба проходят")
@check_roles(ROLE_NONE)
class _ActionTwoCheckersAction(BaseAction[_MockParams, _MockResult]):
    """Два чекера на одном аспекте: result_string и result_float."""

    @regular_aspect("two checkers")
    @result_string("name", required=True)
    @result_float("amount", required=True, min_value=0.0)
    async def two_checkers_aspect(self, params, state, box, connections):
        return {"name": "test", "amount": 99.9}

    @summary_aspect("summary")
    async def build_summary(self, params, state, box, connections):
        return _MockResult()


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def machine() -> ActionProductMachine:
    """ActionProductMachine с тихим логгером."""
    return ActionProductMachine(
        mode="test",
        log_coordinator=LogCoordinator(loggers=[]),
    )


@pytest.fixture()
def context() -> Context:
    """Контекст с ролями manager и admin для прохождения любых проверок."""
    return Context(user=UserInfo(user_id="tester", roles=["manager", "admin"]))


# ═════════════════════════════════════════════════════════════════════════════
# Правило 1 — Regular-аспект вернул не dict
# ═════════════════════════════════════════════════════════════════════════════


class TestNotDictReturn:
    """Regular-аспект обязан возвращать dict. Любой другой тип — TypeError."""

    @pytest.mark.asyncio
    async def test_string_return_raises_type_error(self, machine, context) -> None:
        """
        Regular-аспект возвращает "not a dict" → TypeError.

        ActionProductMachine._execute_regular_aspects() проверяет:
        if not isinstance(new_state_dict, dict): raise TypeError.
        """
        # Arrange — действие с аспектом, возвращающим строку
        action = _ActionBadReturnAction()
        params = _MockParams()

        # Act & Assert — TypeError с указанием имени аспекта
        with pytest.raises(TypeError, match="must return a dict"):
            await machine.run(context, action, params)


# ═════════════════════════════════════════════════════════════════════════════
# Правило 2 — Нет чекеров
# ═════════════════════════════════════════════════════════════════════════════


class TestNoCheckers:
    """Аспект без чекеров: пустой dict OK, непустой dict — ошибка."""

    @pytest.mark.asyncio
    async def test_empty_return_without_checkers_ok(self, machine, context) -> None:
        """
        Regular-аспект без чекеров возвращает {} → OK.
        """
        # Arrange — действие без чекеров, аспект возвращает {}
        action = _ActionNoCheckersEmptyReturnAction()
        params = _MockParams()

        # Act — конвейер завершается без ошибок
        result = await machine.run(context, action, params)

        # Assert — результат от summary-аспекта
        assert isinstance(result, _MockResult)

    @pytest.mark.asyncio
    async def test_non_empty_return_without_checkers_raises(self, machine, context) -> None:
        """
        Regular-аспект без чекеров возвращает {"field": "value"} →
        ValidationFieldError.
        """
        # Arrange — действие без чекеров, аспект возвращает непустой dict
        action = _ActionNoCheckersNonEmptyReturnAction()
        params = _MockParams()

        # Act & Assert — ValidationFieldError с указанием аспекта
        with pytest.raises(ValidationFieldError, match="has no checkers"):
            await machine.run(context, action, params)


# ═════════════════════════════════════════════════════════════════════════════
# Правило 3 — Чекеры: лишние поля и проверка типов
# ═════════════════════════════════════════════════════════════════════════════


class TestCheckerValidation:
    """Чекеры проверяют объявленные поля и отклоняют лишние."""

    @pytest.mark.asyncio
    async def test_extra_field_raises(self, machine, context) -> None:
        """
        Аспект возвращает {"field": "ok", "extra": "forbidden"} →
        ValidationFieldError.
        """
        # Arrange — действие с одним чекером, аспект возвращает лишнее поле
        action = _ActionExtraFieldAction()
        params = _MockParams()

        # Act & Assert — ValidationFieldError с указанием лишнего поля
        with pytest.raises(ValidationFieldError, match="extra"):
            await machine.run(context, action, params)

    @pytest.mark.asyncio
    async def test_wrong_type_raises(self, machine, context) -> None:
        """
        Аспект возвращает {"name": 42} где ожидается строка →
        ValidationFieldError.
        """
        # Arrange — действие с чекером string, аспект возвращает int
        action = _ActionWrongTypeAction()
        params = _MockParams()

        # Act & Assert — ValidationFieldError от ResultStringChecker
        with pytest.raises(ValidationFieldError, match="должен быть строкой"):
            await machine.run(context, action, params)

    @pytest.mark.asyncio
    async def test_two_checkers_both_pass(self, machine, context) -> None:
        """
        Аспект с двумя чекерами (result_string + result_float) — оба
        поля корректны → конвейер завершается без ошибок.
        """
        # Arrange — действие с двумя чекерами, аспект возвращает оба поля
        action = _ActionTwoCheckersAction()
        params = _MockParams()

        # Act — конвейер завершается успешно
        result = await machine.run(context, action, params)

        # Assert — результат от summary
        assert isinstance(result, _MockResult)


# ═════════════════════════════════════════════════════════════════════════════
# Интеграция с доменной моделью
# ═════════════════════════════════════════════════════════════════════════════


class TestDomainModelCheckers:
    """Чекеры доменных действий проходят при корректных данных."""

    @pytest.mark.asyncio
    async def test_simple_action_checker_passes(self, machine, context) -> None:
        """
        SimpleAction: validate_name_aspect с @result_string("validated_name") → OK.
        """
        # Arrange — SimpleAction с корректным именем
        action = SimpleAction()
        params = SimpleAction.Params(name="Alice")

        # Act — конвейер с чекером
        result = await machine.run(context, action, params)

        # Assert — чекер прошёл, greeting сформирован
        assert result.greeting == "Hello, Alice!"

    @pytest.mark.asyncio
    async def test_full_action_checkers_pass(self, machine, context) -> None:
        """
        FullAction: два regular-аспекта с чекерами → оба проходят.
        """
        # Arrange — FullAction с моками зависимостей
        mock_payment = AsyncMock(spec=PaymentService)
        mock_payment.charge.return_value = "TXN-001"
        mock_notification = AsyncMock(spec=NotificationService)
        mock_db = AsyncMock(spec=TestDbManager)

        action = FullAction()
        params = FullAction.Params(user_id="u1", amount=500.0)

        # Act — конвейер с двумя чекерами через _run_internal с моками
        result = await machine._run_internal(
            context=context,
            action=action,
            params=params,
            resources={PaymentService: mock_payment, NotificationService: mock_notification},
            connections={"db": mock_db},
            nested_level=0,
            rollup=False,
        )

        # Assert — оба чекера прошли, результат содержит данные
        assert result.txn_id == "TXN-001"
        assert result.total == 500.0
        assert result.order_id == "ORD-u1"
        assert result.status == "created"
