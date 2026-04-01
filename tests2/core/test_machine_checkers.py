# tests2/core/test_machine_checkers.py
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
   Regular-аспект обязан возвращать dict (или пустой dict {}),
   который мержится в state.

2. Если аспект НЕ имеет чекеров и вернул НЕПУСТОЙ dict → ValidationFieldError.
   Все поля в state должны быть объявлены через чекеры. Если чекеров нет,
   но аспект вернул данные — это ошибка: либо забыли чекеры, либо аспект
   не должен возвращать данные.

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
    - SimpleAction: validate_name с result_string → OK.
    - FullAction: process_payment (result_string) + calc_total (result_float) → OK.
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
from tests2.domain import FullAction, NotificationService, PaymentService, SimpleAction, TestDbManager

# ═════════════════════════════════════════════════════════════════════════════
# Намеренно сломанные действия для edge-case тестов
# ═════════════════════════════════════════════════════════════════════════════


class _MockParams(BaseParams):
    """Пустые параметры для edge-case действий."""
    pass


class _MockResult(BaseResult):
    """Пустой результат для edge-case действий."""
    pass


@meta(description="Аспект возвращает не dict — TypeError")
@check_roles(ROLE_NONE)
class _ActionBadReturn(BaseAction[_MockParams, _MockResult]):
    """Regular-аспект возвращает строку вместо dict."""

    @regular_aspect("bad")
    async def bad_aspect(self, params, state, box, connections):
        return "not a dict"

    @summary_aspect("summary")
    async def summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Нет чекеров, но вернул непустой dict")
@check_roles(ROLE_NONE)
class _ActionNoCheckersNonEmptyReturn(BaseAction[_MockParams, _MockResult]):
    """Regular-аспект без чекеров возвращает данные — ValidationFieldError."""

    @regular_aspect("no checkers")
    async def aspect_no_checkers(self, params, state, box, connections):
        return {"field": "value"}

    @summary_aspect("summary")
    async def summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Нет чекеров, вернул пустой dict")
@check_roles(ROLE_NONE)
class _ActionNoCheckersEmptyReturn(BaseAction[_MockParams, _MockResult]):
    """Regular-аспект без чекеров возвращает {} — OK."""

    @regular_aspect("no checkers empty")
    async def aspect_empty(self, params, state, box, connections):
        return {}

    @summary_aspect("summary")
    async def summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Чекер на одно поле, но возвращает лишнее")
@check_roles(ROLE_NONE)
class _ActionExtraField(BaseAction[_MockParams, _MockResult]):
    """Аспект с чекером на field, но возвращает ещё extra."""

    @regular_aspect("extra field")
    @result_string("field", required=True)
    async def aspect_extra(self, params, state, box, connections):
        return {"field": "ok", "extra": "forbidden"}

    @summary_aspect("summary")
    async def summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Чекер ожидает строку, аспект возвращает int")
@check_roles(ROLE_NONE)
class _ActionWrongType(BaseAction[_MockParams, _MockResult]):
    """Аспект возвращает int в поле, где ожидается строка."""

    @regular_aspect("wrong type")
    @result_string("name", required=True)
    async def aspect_wrong_type(self, params, state, box, connections):
        return {"name": 42}  # int вместо str

    @summary_aspect("summary")
    async def summary(self, params, state, box, connections):
        return _MockResult()


@meta(description="Два чекера, оба проходят")
@check_roles(ROLE_NONE)
class _ActionTwoCheckers(BaseAction[_MockParams, _MockResult]):
    """Два чекера на одном аспекте: result_string и result_float."""

    @regular_aspect("two checkers")
    @result_string("name", required=True)
    @result_float("amount", required=True, min_value=0.0)
    async def aspect_two(self, params, state, box, connections):
        return {"name": "test", "amount": 99.9}

    @summary_aspect("summary")
    async def summary(self, params, state, box, connections):
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
        Сообщение содержит имя аспекта и фактический тип.
        """
        # Arrange — действие с аспектом, возвращающим строку
        action = _ActionBadReturn()
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

        Пустой dict — валидный результат: аспект выполнил побочный эффект
        (логирование, проверку), но не записал данные в state.
        """
        # Arrange — действие без чекеров, аспект возвращает {}
        action = _ActionNoCheckersEmptyReturn()
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

        Машина требует, чтобы все поля в state были объявлены через чекеры.
        Если аспект возвращает данные без чекеров — это баг: либо забыли
        добавить чекеры, либо аспект не должен возвращать данные.
        """
        # Arrange — действие без чекеров, аспект возвращает непустой dict
        action = _ActionNoCheckersNonEmptyReturn()
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

        Чекер объявлен только для "field". Поле "extra" не объявлено.
        Машина проверяет: set(result.keys()) - allowed_fields → {"extra"} →
        ValidationFieldError с перечислением лишних полей.
        """
        # Arrange — действие с одним чекером, аспект возвращает лишнее поле
        action = _ActionExtraField()
        params = _MockParams()

        # Act & Assert — ValidationFieldError с указанием лишнего поля
        with pytest.raises(ValidationFieldError, match="extra"):
            await machine.run(context, action, params)

    @pytest.mark.asyncio
    async def test_wrong_type_raises(self, machine, context) -> None:
        """
        Аспект возвращает {"name": 42} где ожидается строка →
        ValidationFieldError.

        Чекер result_string("name") проверяет isinstance(value, str).
        42 — int, не str → ValidationFieldError с указанием поля и типа.
        """
        # Arrange — действие с чекером string, аспект возвращает int
        action = _ActionWrongType()
        params = _MockParams()

        # Act & Assert — ValidationFieldError от ResultStringChecker
        with pytest.raises(ValidationFieldError, match="должен быть строкой"):
            await machine.run(context, action, params)

    @pytest.mark.asyncio
    async def test_two_checkers_both_pass(self, machine, context) -> None:
        """
        Аспект с двумя чекерами (result_string + result_float) — оба
        поля корректны → конвейер завершается без ошибок.

        Машина применяет все чекеры последовательно через
        _apply_checkers(). Если все проходят — state обновляется.
        """
        # Arrange — действие с двумя чекерами, аспект возвращает оба поля
        action = _ActionTwoCheckers()
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
        SimpleAction: validate_name с @result_string("validated_name") → OK.

        validate_name возвращает {"validated_name": params.name.strip()}.
        Чекер result_string проверяет: isinstance(str) и min_length=1.
        Имя "Alice" → "Alice" → проходит.
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

        process_payment: @result_string("txn_id", min_length=1) → "TXN-001".
        calc_total: @result_float("total", min_value=0.0) → 500.0.
        Оба чекера проходят → summary формирует Result.
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
