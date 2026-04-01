# tests2/metadata/test_builder_checkers.py
"""
Тесты MetadataBuilder — сборка чекеров результата аспектов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что MetadataBuilder корректно собирает чекеры (CheckerMeta)
из декораторов result_string, result_int и др., привязанных к методам-
аспектам. Чекеры должны быть привязаны к конкретному аспекту по
method_name. Чекер на методе без _new_aspect_meta вызывает ошибку.

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

TestCheckersOnAspect
    - Один чекер на regular-аспекте → checkers содержит один элемент.
    - Два чекера на одном аспекте → оба собираются.
    - Чекеры на разных аспектах → get_checkers_for_aspect фильтрует.

TestCheckerAttributes
    - checker_class сохраняется.
    - field_name сохраняется.
    - required сохраняется.
    - method_name привязан к аспекту.

TestCheckerWithoutAspect
    - Чекер на методе без @regular_aspect/@summary_aspect → ошибка.

TestCheckerGateHost
    - Чекеры на классе без CheckerGateHost → ошибка.
"""

import pytest

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import check_roles
from action_machine.auth.constants import ROLE_NONE
from action_machine.checkers.result_int_checker import ResultIntChecker, result_int
from action_machine.checkers.result_string_checker import ResultStringChecker, result_string
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.meta_decorator import meta
from action_machine.metadata.builder import MetadataBuilder

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные классы
# ═════════════════════════════════════════════════════════════════════════════


class _Params(BaseParams):
    """Параметры для тестовых действий."""
    pass


class _Result(BaseResult):
    """Результат для тестовых действий."""
    pass


@meta("Действие с одним чекером")
@check_roles(ROLE_NONE)
class _ActionOneChecker(BaseAction["_Params", "_Result"]):
    """Действие с одним result_string чекером на regular-аспекте."""

    @regular_aspect("Получение имени")
    @result_string("name", required=True)
    async def get_name(self, params, state, box, connections):
        return {"name": "Alice"}

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {"result": "ok"}


@meta("Действие с двумя чекерами на одном аспекте")
@check_roles(ROLE_NONE)
class _ActionTwoCheckersOneAspect(BaseAction["_Params", "_Result"]):
    """Действие с двумя чекерами на одном regular-аспекте."""

    @regular_aspect("Получение данных")
    @result_string("name", required=True)
    @result_int("age", required=True)
    async def get_data(self, params, state, box, connections):
        return {"name": "Alice", "age": 30}

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {"result": "ok"}


@meta("Действие с чекерами на разных аспектах")
@check_roles(ROLE_NONE)
class _ActionCheckersOnDifferentAspects(BaseAction["_Params", "_Result"]):
    """Действие с чекерами на разных regular-аспектах."""

    @regular_aspect("Шаг 1")
    @result_string("name", required=True)
    async def step_one(self, params, state, box, connections):
        return {"name": "Alice"}

    @regular_aspect("Шаг 2")
    @result_int("count", required=True)
    async def step_two(self, params, state, box, connections):
        return {"count": 42}

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {"result": "ok"}


# ═════════════════════════════════════════════════════════════════════════════
# Чекеры на аспекте
# ═════════════════════════════════════════════════════════════════════════════


class TestCheckersOnAspect:
    """Проверяет сборку чекеров, привязанных к аспектам."""

    def test_single_checker_collected(self):
        """Один чекер собирается в metadata.checkers."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionOneChecker)

        # Assert
        assert result.has_checkers() is True
        assert len(result.checkers) == 1

    def test_two_checkers_on_one_aspect(self):
        """Два чекера на одном аспекте — оба собираются."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionTwoCheckersOneAspect)

        # Assert
        assert len(result.checkers) == 2

    def test_checkers_on_different_aspects(self):
        """Чекеры на разных аспектах — все собираются."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionCheckersOnDifferentAspects)

        # Assert
        assert len(result.checkers) == 2

    def test_get_checkers_for_aspect_filters(self):
        """get_checkers_for_aspect фильтрует чекеры по method_name."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionCheckersOnDifferentAspects)

        # Assert
        step_one_checkers = result.get_checkers_for_aspect("step_one")
        step_two_checkers = result.get_checkers_for_aspect("step_two")
        assert len(step_one_checkers) == 1
        assert step_one_checkers[0].field_name == "name"
        assert len(step_two_checkers) == 1
        assert step_two_checkers[0].field_name == "count"

    def test_get_checkers_for_nonexistent_aspect(self):
        """get_checkers_for_aspect для несуществующего аспекта — пустой кортеж."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionOneChecker)

        # Assert
        assert result.get_checkers_for_aspect("nonexistent") == ()


# ═════════════════════════════════════════════════════════════════════════════
# Атрибуты чекера
# ═════════════════════════════════════════════════════════════════════════════


class TestCheckerAttributes:
    """Проверяет, что атрибуты CheckerMeta корректно заполняются."""

    def test_checker_class_preserved(self):
        """checker_class сохраняет класс чекера."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionOneChecker)
        checker = result.checkers[0]

        # Assert
        assert checker.checker_class is ResultStringChecker

    def test_field_name_preserved(self):
        """field_name сохраняет имя поля."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionOneChecker)
        checker = result.checkers[0]

        # Assert
        assert checker.field_name == "name"

    def test_required_preserved(self):
        """required сохраняет значение True."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionOneChecker)
        checker = result.checkers[0]

        # Assert
        assert checker.required is True

    def test_method_name_matches_aspect(self):
        """method_name чекера совпадает с именем аспекта."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionOneChecker)
        checker = result.checkers[0]

        # Assert
        assert checker.method_name == "get_name"

    def test_two_checkers_have_different_classes(self):
        """Два чекера разных типов сохраняют свои классы."""
        # Arrange & Act
        result = MetadataBuilder().build(_ActionTwoCheckersOneAspect)
        classes = {c.checker_class for c in result.checkers}

        # Assert
        assert ResultStringChecker in classes
        assert ResultIntChecker in classes


# ═════════════════════════════════════════════════════════════════════════════
# Чекер без аспекта
# ═════════════════════════════════════════════════════════════════════════════


class TestCheckerWithoutAspect:
    """Проверяет, что чекер на методе без аспекта вызывает ошибку."""

    def test_checker_on_non_aspect_raises(self):
        """Чекер на обычном методе (без @regular_aspect) — ошибка при сборке."""
        # Arrange
        @meta("Чекер без аспекта")
        @check_roles(ROLE_NONE)
        class _BadAction(BaseAction["_Params", "_Result"]):

            @result_string("name", required=True)
            async def not_an_aspect(self, params, state, box, connections):
                return {"name": "Alice"}

            @summary_aspect("Итог")
            async def finalize(self, params, state, box, connections):
                return {"result": "ok"}

        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            MetadataBuilder().build(_BadAction)


# ═════════════════════════════════════════════════════════════════════════════
# Чекеры без CheckerGateHost
# ═════════════════════════════════════════════════════════════════════════════


class TestCheckerGateHost:
    """Проверяет, что чекеры на классе без CheckerGateHost вызывают ошибку."""

    def test_checkers_without_host_raises(self):
        """Чекеры на классе без CheckerGateHost отклоняются."""
        # Arrange — класс, не наследующий CheckerGateHost
        class _NoHost:
            @regular_aspect("Шаг")
            @result_string("name")
            async def step(self, params, state, box, connections):
                return {"name": "value"}

            @summary_aspect("Итог")
            async def finalize(self, params, state, box, connections):
                return {}

        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            MetadataBuilder().build(_NoHost)
