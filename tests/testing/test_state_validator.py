# tests/testing/test_state_validator.py
"""
Тесты для модуля валидации state перед выполнением аспектов.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

validate_state_for_aspect:
    - Первый аспект — нет предшествующих, любой state допустим.
    - Второй аспект с корректным state от первого — проходит.
    - Обязательное поле предшествующего аспекта отсутствует — ошибка.
    - Поле присутствует, но неверного типа — ошибка от чекера.
    - Нарушение constraint (min_length, min_value) — ошибка от чекера.
    - Необязательное поле отсутствует — проходит.
    - Необязательное поле с неверным типом — ошибка.
    - Несуществующий аспект — ошибка.
    - Предшествующие аспекты без чекеров — любой state допустим.
    - Третий аспект проверяет поля первого и второго.
    - Сообщение об ошибке содержит имя аспекта-источника и класс чекера.

validate_state_for_summary:
    - Полный state со всеми обязательными полями — проходит.
    - Отсутствует поле любого из regular-аспектов — ошибка.
    - Поле неверного типа — ошибка от чекера.
    - Нарушение constraint — ошибка от чекера.
    - Действие без regular-аспектов — любой state допустим.
    - Аспекты без чекеров — любой state допустим.
    - Лишние поля в state не вызывают ошибок.
    - Сообщение об ошибке содержит "Summary" и имя аспекта-источника.
"""

import pytest

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.checkers import result_float, result_int, result_string
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.gate_coordinator import GateCoordinator
from action_machine.core.meta_decorator import meta
from action_machine.testing.state_validator import (
    StateValidationError,
    validate_state_for_aspect,
    validate_state_for_summary,
)

# ═════════════════════════════════════════════════════════════════════════════
# Тестовые действия
# ═════════════════════════════════════════════════════════════════════════════


class SimpleParams(BaseParams):
    """Пустые параметры."""
    pass


class SimpleResult(BaseResult):
    """Пустой результат."""
    pass


@meta(description="Три regular-аспекта с чекерами разных типов")
@check_roles(ROLE_NONE)
class ThreeAspectAction(BaseAction[SimpleParams, SimpleResult]):
    """
    validate  → validated_user (str, required, min_length=1)
    process   → txn_id (str, required), amount (float, required, min_value=0.0)
    finalize  → code (int, required, min_value=0)
    """

    @regular_aspect("Валидация")
    @result_string("validated_user", required=True, min_length=1)
    async def validate(self, params, state, box, connections):
        """Записывает validated_user."""
        return {"validated_user": "user_1"}

    @regular_aspect("Обработка")
    @result_string("txn_id", required=True)
    @result_float("amount", required=True, min_value=0.0)
    async def process(self, params, state, box, connections):
        """Записывает txn_id и amount."""
        return {"txn_id": "TXN-1", "amount": 100.0}

    @regular_aspect("Финализация")
    @result_int("code", required=True, min_value=0)
    async def finalize(self, params, state, box, connections):
        """Записывает code."""
        return {"code": 200}

    @summary_aspect("Результат")
    async def build_result(self, params, state, box, connections):
        """Собирает результат."""
        return SimpleResult()


@meta(description="Действие с необязательным полем в чекере")
@check_roles(ROLE_NONE)
class OptionalFieldAction(BaseAction[SimpleParams, SimpleResult]):
    """
    step1 → optional_note (str, optional)
    step2 → data (str, required)
    """

    @regular_aspect("Шаг 1")
    @result_string("optional_note", required=False)
    async def step1(self, params, state, box, connections):
        """Необязательное поле."""
        return {}

    @regular_aspect("Шаг 2")
    @result_string("data", required=True)
    async def step2(self, params, state, box, connections):
        """Обязательное поле."""
        return {"data": "value"}

    @summary_aspect("Итог")
    async def build_result(self, params, state, box, connections):
        """Собирает результат."""
        return SimpleResult()


@meta(description="Действие с аспектами без чекеров")
@check_roles(ROLE_NONE)
class NoCheckersAction(BaseAction[SimpleParams, SimpleResult]):
    """Аспекты без чекеров — ничего не записывают в state."""

    @regular_aspect("Пустой шаг")
    async def empty_step(self, params, state, box, connections):
        """Возвращает пустой dict."""
        return {}

    @summary_aspect("Итог")
    async def build_result(self, params, state, box, connections):
        """Собирает результат."""
        return SimpleResult()


@meta(description="Действие только с summary")
@check_roles(ROLE_NONE)
class SummaryOnlyAction(BaseAction[SimpleParams, SimpleResult]):
    """Нет regular-аспектов."""

    @summary_aspect("Только summary")
    async def build_result(self, params, state, box, connections):
        """Результат без конвейера."""
        return SimpleResult()


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def coordinator() -> GateCoordinator:
    return GateCoordinator()


@pytest.fixture
def three_aspect_meta(coordinator):
    return coordinator.get(ThreeAspectAction)


@pytest.fixture
def optional_field_meta(coordinator):
    return coordinator.get(OptionalFieldAction)


@pytest.fixture
def no_checkers_meta(coordinator):
    return coordinator.get(NoCheckersAction)


@pytest.fixture
def summary_only_meta(coordinator):
    return coordinator.get(SummaryOnlyAction)


# ═════════════════════════════════════════════════════════════════════════════
# validate_state_for_aspect — первый аспект
# ═════════════════════════════════════════════════════════════════════════════


class TestFirstAspect:
    """Первый аспект не имеет предшествующих — валидация state не нужна."""

    def test_empty_state(self, three_aspect_meta):
        """Пустой state допустим для первого аспекта — нет предшествующих чекеров."""
        validate_state_for_aspect(three_aspect_meta, "validate", {})

    def test_arbitrary_state(self, three_aspect_meta):
        """Произвольный state допустим для первого аспекта — ничего не проверяется."""
        validate_state_for_aspect(three_aspect_meta, "validate", {"random": 42})


# ═════════════════════════════════════════════════════════════════════════════
# validate_state_for_aspect — второй аспект
# ═════════════════════════════════════════════════════════════════════════════


class TestSecondAspect:
    """Второй аспект (process) зависит от поля validated_user первого аспекта (validate)."""

    def test_valid_state(self, three_aspect_meta):
        """State с корректным validated_user от первого аспекта — проходит."""
        validate_state_for_aspect(three_aspect_meta, "process", {"validated_user": "u1"})

    def test_missing_required_field(self, three_aspect_meta):
        """
        Проверяет, что отсутствие обязательного поля от предшествующего аспекта
        обнаруживается до выполнения:

        1. Бросает StateValidationError — не даёт аспекту упасть с KeyError.
        2. Сообщение содержит имя поля (validated_user) — тестировщик знает что добавить.
        3. Атрибут source_aspect указывает на аспект-источник (validate).
        """
        with pytest.raises(StateValidationError) as exc_info:
            validate_state_for_aspect(three_aspect_meta, "process", {})

        err = exc_info.value
        assert err.field == "validated_user"
        assert err.source_aspect == "validate"

    def test_wrong_type(self, three_aspect_meta):
        """validated_user=123 вместо строки — чекер ResultStringChecker отклоняет."""
        with pytest.raises(StateValidationError, match="должен быть строкой"):
            validate_state_for_aspect(three_aspect_meta, "process", {"validated_user": 123})

    def test_empty_string_violates_min_length(self, three_aspect_meta):
        """validated_user="" при min_length=1 — нарушение constraint."""
        with pytest.raises(StateValidationError, match="validated_user"):
            validate_state_for_aspect(three_aspect_meta, "process", {"validated_user": ""})


# ═════════════════════════════════════════════════════════════════════════════
# validate_state_for_aspect — третий аспект
# ═════════════════════════════════════════════════════════════════════════════


class TestThirdAspect:
    """Третий аспект (finalize) зависит от полей первого (validate) и второго (process)."""

    def test_complete_state(self, three_aspect_meta):
        """State со всеми полями от первого и второго аспектов — проходит."""
        validate_state_for_aspect(three_aspect_meta, "finalize", {
            "validated_user": "u1",
            "txn_id": "TXN-1",
            "amount": 100.0,
        })

    def test_missing_first_aspect_field(self, three_aspect_meta):
        """Нет validated_user от первого аспекта — ошибка даже при наличии полей второго."""
        with pytest.raises(StateValidationError, match="validated_user"):
            validate_state_for_aspect(three_aspect_meta, "finalize", {
                "txn_id": "TXN-1",
                "amount": 100.0,
            })

    def test_missing_second_aspect_field(self, three_aspect_meta):
        """
        Нет полей от второго аспекта (process) — ошибка на первом отсутствующем поле.

        У process два чекера (txn_id, amount). Декораторы применяются снизу вверх,
        поэтому порядок проверки зависит от порядка в _checker_meta. Ловим по аспекту-источнику.
        """
        with pytest.raises(StateValidationError, match="от аспекта 'process'"):
            validate_state_for_aspect(three_aspect_meta, "finalize", {
                "validated_user": "u1",
            })

    def test_wrong_type_in_second_aspect_field(self, three_aspect_meta):
        """amount="строка" вместо float — чекер ResultFloatChecker отклоняет."""
        with pytest.raises(StateValidationError, match="amount"):
            validate_state_for_aspect(three_aspect_meta, "finalize", {
                "validated_user": "u1",
                "txn_id": "TXN-1",
                "amount": "не число",
            })


# ═════════════════════════════════════════════════════════════════════════════
# validate_state_for_aspect — необязательные поля
# ═════════════════════════════════════════════════════════════════════════════


class TestOptionalFields:
    """Необязательные поля: отсутствие допустимо, неверный тип — ошибка."""

    def test_absent_optional_field(self, optional_field_meta):
        """optional_note отсутствует в state — допустимо, required=False."""
        validate_state_for_aspect(optional_field_meta, "step2", {})

    def test_wrong_type_in_optional_field(self, optional_field_meta):
        """optional_note=42 вместо строки — чекер отклоняет даже необязательное поле."""
        with pytest.raises(StateValidationError, match="должен быть строкой"):
            validate_state_for_aspect(optional_field_meta, "step2", {"optional_note": 42})


# ═════════════════════════════════════════════════════════════════════════════
# validate_state_for_aspect — особые случаи
# ═════════════════════════════════════════════════════════════════════════════


class TestAspectEdgeCases:

    def test_nonexistent_aspect(self, three_aspect_meta):
        """Несуществующий аспект — StateValidationError с перечислением доступных."""
        with pytest.raises(StateValidationError, match="не найден"):
            validate_state_for_aspect(three_aspect_meta, "nonexistent", {})

    def test_no_checkers_in_preceding(self, no_checkers_meta):
        """Предшествующие аспекты без чекеров — любой state допустим."""
        validate_state_for_aspect(no_checkers_meta, "build_result", {})
        validate_state_for_aspect(no_checkers_meta, "build_result", {"anything": 42})

    def test_error_contains_source_aspect_name(self, three_aspect_meta):
        """Сообщение об ошибке содержит имя аспекта, который должен был записать поле."""
        with pytest.raises(StateValidationError, match="от аспекта 'validate'"):
            validate_state_for_aspect(three_aspect_meta, "process", {})

    def test_error_contains_checker_class_name(self, three_aspect_meta):
        """Сообщение об ошибке содержит имя класса чекера для диагностики."""
        with pytest.raises(StateValidationError, match="ResultStringChecker"):
            validate_state_for_aspect(three_aspect_meta, "process", {})


# ═════════════════════════════════════════════════════════════════════════════
# validate_state_for_summary — полный state
# ═════════════════════════════════════════════════════════════════════════════


class TestSummaryComplete:
    """Summary-аспект зависит от полей всех regular-аспектов."""

    def test_complete_state(self, three_aspect_meta):
        """Полный state со всеми обязательными полями от всех regular-аспектов — проходит."""
        validate_state_for_summary(three_aspect_meta, {
            "validated_user": "u1",
            "txn_id": "TXN-1",
            "amount": 100.0,
            "code": 200,
        })

    def test_extra_fields_ignored(self, three_aspect_meta):
        """Лишние поля в state не вызывают ошибок — проверяются только объявленные чекерами."""
        validate_state_for_summary(three_aspect_meta, {
            "validated_user": "u1",
            "txn_id": "TXN-1",
            "amount": 100.0,
            "code": 200,
            "extra": "ignored",
        })


# ═════════════════════════════════════════════════════════════════════════════
# validate_state_for_summary — отсутствующие поля
# ═════════════════════════════════════════════════════════════════════════════


class TestSummaryMissing:
    """Отсутствие обязательного поля от любого regular-аспекта — ошибка."""

    def test_missing_first_aspect_field(self, three_aspect_meta):
        """Нет validated_user от первого аспекта."""
        with pytest.raises(StateValidationError, match="validated_user"):
            validate_state_for_summary(three_aspect_meta, {
                "txn_id": "TXN-1", "amount": 100.0, "code": 200,
            })

    def test_missing_second_aspect_field(self, three_aspect_meta):
        """
        Нет полей от второго аспекта (process) — ошибка на первом отсутствующем поле.

        У process два чекера (txn_id, amount). Порядок проверки зависит от порядка
        в _checker_meta. Ловим по аспекту-источнику.
        """
        with pytest.raises(StateValidationError, match="от аспекта 'process'"):
            validate_state_for_summary(three_aspect_meta, {
                "validated_user": "u1", "code": 200,
            })

    def test_missing_third_aspect_field(self, three_aspect_meta):
        """Нет code от третьего аспекта."""
        with pytest.raises(StateValidationError, match="code"):
            validate_state_for_summary(three_aspect_meta, {
                "validated_user": "u1", "txn_id": "TXN-1", "amount": 100.0,
            })


# ═════════════════════════════════════════════════════════════════════════════
# validate_state_for_summary — ошибки типов и constraints
# ═════════════════════════════════════════════════════════════════════════════


class TestSummaryTypeErrors:
    """Поля с неверным типом или нарушением constraint отклоняются."""

    def test_wrong_type(self, three_aspect_meta):
        """txn_id=12345 вместо строки — чекер ResultStringChecker отклоняет."""
        with pytest.raises(StateValidationError, match="txn_id"):
            validate_state_for_summary(three_aspect_meta, {
                "validated_user": "u1", "txn_id": 12345,
                "amount": 100.0, "code": 200,
            })

    def test_float_constraint_violation(self, three_aspect_meta):
        """amount=-5.0 при min_value=0.0 — нарушение constraint."""
        with pytest.raises(StateValidationError, match="amount"):
            validate_state_for_summary(three_aspect_meta, {
                "validated_user": "u1", "txn_id": "TXN-1",
                "amount": -5.0, "code": 200,
            })

    def test_int_constraint_violation(self, three_aspect_meta):
        """code=-1 при min_value=0 — нарушение constraint."""
        with pytest.raises(StateValidationError, match="code"):
            validate_state_for_summary(three_aspect_meta, {
                "validated_user": "u1", "txn_id": "TXN-1",
                "amount": 100.0, "code": -1,
            })


# ═════════════════════════════════════════════════════════════════════════════
# validate_state_for_summary — особые случаи
# ═════════════════════════════════════════════════════════════════════════════


class TestSummaryEdgeCases:

    def test_summary_only_action(self, summary_only_meta):
        """Действие без regular-аспектов — пустой state допустим."""
        validate_state_for_summary(summary_only_meta, {})

    def test_no_checkers_action(self, no_checkers_meta):
        """Аспекты без чекеров — любой state допустим для summary."""
        validate_state_for_summary(no_checkers_meta, {})

    def test_error_says_summary(self, three_aspect_meta):
        """Сообщение об ошибке начинается с 'Summary' — понятно что проверяем state для summary."""
        with pytest.raises(StateValidationError, match="^Summary"):
            validate_state_for_summary(three_aspect_meta, {})

    def test_error_contains_source_aspect(self, three_aspect_meta):
        """Сообщение содержит имя аспекта, от которого ожидается отсутствующее поле."""
        with pytest.raises(StateValidationError, match="от аспекта 'validate'"):
            validate_state_for_summary(three_aspect_meta, {})
