# tests2/metadata/test_builder_aspects.py
"""
Тесты MetadataBuilder — сборка аспектов и структурные инварианты.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что MetadataBuilder корректно собирает аспекты (regular и summary)
из методов класса, сохраняет порядок, проверяет структурные инварианты
(ровно один summary, summary последний, regular без summary запрещён).

═══════════════════════════════════════════════════════════════════════════════
СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

TestRegularAndSummary
    - Один regular + один summary → два аспекта в metadata.
    - Порядок аспектов сохраняется (regular первый, summary последний).
    - method_ref — callable, указывающий на оригинальный метод.

TestOnlySummary
    - Класс с только summary-аспектом — валидно.

TestMultipleRegular
    - Два regular + summary → три аспекта, порядок сохранён.

TestStructuralErrors
    - Два summary-аспекта → ValueError.
    - Regular без summary → ValueError.
    - Summary не последний → ValueError.

TestAspectsWithoutGateHost
    - Аспекты на классе без AspectGateHost → ошибка.

TestAspectsRequireMeta
    - Аспекты на классе без @meta → TypeError.
"""

import pytest

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import check_roles
from action_machine.auth.constants import ROLE_NONE
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


@meta("Действие с одним regular и одним summary")
@check_roles(ROLE_NONE)
class _OneRegularOneSummary(BaseAction["_Params", "_Result"]):
    """Действие с одним regular-аспектом и одним summary-аспектом."""

    @regular_aspect("Шаг 1")
    async def step_one(self, params, state, box, connections):
        return {"data": "value"}

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {"result": "done"}


@meta("Действие только с summary")
@check_roles(ROLE_NONE)
class _OnlySummary(BaseAction["_Params", "_Result"]):
    """Действие с только summary-аспектом — валидно."""

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {"result": "done"}


@meta("Действие с двумя regular и одним summary")
@check_roles(ROLE_NONE)
class _TwoRegularOneSummary(BaseAction["_Params", "_Result"]):
    """Действие с двумя regular-аспектами и одним summary."""

    @regular_aspect("Шаг 1")
    async def step_one(self, params, state, box, connections):
        return {"a": 1}

    @regular_aspect("Шаг 2")
    async def step_two(self, params, state, box, connections):
        return {"b": 2}

    @summary_aspect("Итог")
    async def finalize(self, params, state, box, connections):
        return {"result": "done"}


# ═════════════════════════════════════════════════════════════════════════════
# Regular + Summary
# ═════════════════════════════════════════════════════════════════════════════


class TestRegularAndSummary:
    """Проверяет сборку одного regular и одного summary аспекта."""

    def test_two_aspects_collected(self):
        """Builder собирает два аспекта."""
        # Arrange & Act
        result = MetadataBuilder().build(_OneRegularOneSummary)

        # Assert
        assert result.has_aspects() is True
        assert len(result.aspects) == 2

    def test_first_aspect_is_regular(self):
        """Первый аспект — regular."""
        # Arrange & Act
        result = MetadataBuilder().build(_OneRegularOneSummary)

        # Assert
        assert result.aspects[0].aspect_type == "regular"

    def test_last_aspect_is_summary(self):
        """Последний аспект — summary."""
        # Arrange & Act
        result = MetadataBuilder().build(_OneRegularOneSummary)

        # Assert
        assert result.aspects[-1].aspect_type == "summary"

    def test_method_name_preserved(self):
        """method_name сохраняет имя метода."""
        # Arrange & Act
        result = MetadataBuilder().build(_OneRegularOneSummary)

        # Assert
        assert result.aspects[0].method_name == "step_one"
        assert result.aspects[1].method_name == "finalize"

    def test_description_preserved(self):
        """description сохраняет описание из декоратора."""
        # Arrange & Act
        result = MetadataBuilder().build(_OneRegularOneSummary)

        # Assert
        assert result.aspects[0].description == "Шаг 1"
        assert result.aspects[1].description == "Итог"

    def test_method_ref_is_callable(self):
        """method_ref — вызываемый объект."""
        # Arrange & Act
        result = MetadataBuilder().build(_OneRegularOneSummary)

        # Assert
        assert callable(result.aspects[0].method_ref)
        assert callable(result.aspects[1].method_ref)


# ═════════════════════════════════════════════════════════════════════════════
# Только Summary
# ═════════════════════════════════════════════════════════════════════════════


class TestOnlySummary:
    """Проверяет, что класс с только summary-аспектом — валидный."""

    def test_single_summary_collected(self):
        """Builder собирает один summary-аспект."""
        # Arrange & Act
        result = MetadataBuilder().build(_OnlySummary)

        # Assert
        assert len(result.aspects) == 1
        assert result.aspects[0].aspect_type == "summary"

    def test_get_summary_aspect(self):
        """get_summary_aspect возвращает summary-аспект."""
        # Arrange & Act
        result = MetadataBuilder().build(_OnlySummary)

        # Assert
        summary = result.get_summary_aspect()
        assert summary is not None
        assert summary.method_name == "finalize"

    def test_get_regular_aspects_empty(self):
        """get_regular_aspects возвращает пустой кортеж."""
        # Arrange & Act
        result = MetadataBuilder().build(_OnlySummary)

        # Assert
        assert result.get_regular_aspects() == ()


# ═════════════════════════════════════════════════════════════════════════════
# Несколько Regular
# ═════════════════════════════════════════════════════════════════════════════


class TestMultipleRegular:
    """Проверяет сборку нескольких regular-аспектов."""

    def test_three_aspects_collected(self):
        """Builder собирает три аспекта (два regular + один summary)."""
        # Arrange & Act
        result = MetadataBuilder().build(_TwoRegularOneSummary)

        # Assert
        assert len(result.aspects) == 3

    def test_regular_aspects_order(self):
        """Порядок regular-аспектов сохраняется."""
        # Arrange & Act
        result = MetadataBuilder().build(_TwoRegularOneSummary)
        regular = result.get_regular_aspects()

        # Assert
        assert len(regular) == 2
        assert regular[0].method_name == "step_one"
        assert regular[1].method_name == "step_two"

    def test_summary_is_last(self):
        """Summary-аспект последний в списке."""
        # Arrange & Act
        result = MetadataBuilder().build(_TwoRegularOneSummary)

        # Assert
        assert result.aspects[-1].aspect_type == "summary"
        assert result.aspects[-1].method_name == "finalize"


# ═════════════════════════════════════════════════════════════════════════════
# Структурные ошибки
# ═════════════════════════════════════════════════════════════════════════════


class TestStructuralErrors:
    """Проверяет, что Builder отклоняет некорректные структуры аспектов."""

    def test_two_summaries_raises(self):
        """Два summary-аспекта вызывают ValueError."""
        # Arrange — определяем класс с двумя summary внутри теста
        with pytest.raises(ValueError, match="summary"):

            @meta("Два summary")
            @check_roles(ROLE_NONE)
            class _TwoSummaries(BaseAction["_Params", "_Result"]):

                @summary_aspect("Итог 1")
                async def summary_one(self, params, state, box, connections):
                    return {}

                @summary_aspect("Итог 2")
                async def summary_two(self, params, state, box, connections):
                    return {}

            MetadataBuilder().build(_TwoSummaries)

    def test_regular_without_summary_raises(self):
        """Regular-аспект без summary вызывает ValueError."""
        # Arrange
        with pytest.raises(ValueError, match="summary"):

            @meta("Regular без summary")
            @check_roles(ROLE_NONE)
            class _RegularOnly(BaseAction["_Params", "_Result"]):

                @regular_aspect("Шаг 1")
                async def step_one(self, params, state, box, connections):
                    return {}

            MetadataBuilder().build(_RegularOnly)

    def test_summary_not_last_raises(self):
        """Summary-аспект не последним вызывает ValueError."""
        # Arrange
        with pytest.raises(ValueError, match="последн"):

            @meta("Summary не последний")
            @check_roles(ROLE_NONE)
            class _SummaryNotLast(BaseAction["_Params", "_Result"]):

                @summary_aspect("Итог")
                async def finalize(self, params, state, box, connections):
                    return {}

                @regular_aspect("Шаг после итога")
                async def late_step(self, params, state, box, connections):
                    return {}

            MetadataBuilder().build(_SummaryNotLast)


# ═════════════════════════════════════════════════════════════════════════════
# Аспекты без GateHost
# ═════════════════════════════════════════════════════════════════════════════


class TestAspectsWithoutGateHost:
    """Проверяет, что аспекты на классе без AspectGateHost вызывают ошибку."""

    def test_aspects_without_host_raises(self):
        """Аспекты на классе без AspectGateHost отклоняются."""
        # Arrange — класс, не наследующий AspectGateHost
        class _NoHost:
            @regular_aspect("Шаг")
            async def step(self, params, state, box, connections):
                return {}

            @summary_aspect("Итог")
            async def finalize(self, params, state, box, connections):
                return {}

        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            MetadataBuilder().build(_NoHost)


# ═════════════════════════════════════════════════════════════════════════════
# Аспекты требуют @meta
# ═════════════════════════════════════════════════════════════════════════════


class TestAspectsRequireMeta:
    """Проверяет, что действие с аспектами без @meta вызывает ошибку."""

    def test_action_with_aspects_without_meta_raises(self):
        """BaseAction с аспектами, но без @meta — TypeError."""
        # Arrange
        @check_roles(ROLE_NONE)
        class _NoMeta(BaseAction["_Params", "_Result"]):

            @regular_aspect("Шаг")
            async def step(self, params, state, box, connections):
                return {"data": 1}

            @summary_aspect("Итог")
            async def finalize(self, params, state, box, connections):
                return {"result": "ok"}

        # Act & Assert
        with pytest.raises(TypeError):
            MetadataBuilder().build(_NoMeta)

    def test_action_without_aspects_without_meta_ok(self):
        """BaseAction без аспектов и без @meta — допустимо."""
        # Arrange
        @check_roles(ROLE_NONE)
        class _NoMetaNoAspects(BaseAction["_Params", "_Result"]):
            pass

        # Act
        result = MetadataBuilder().build(_NoMetaNoAspects)

        # Assert
        assert result.has_meta() is False
        assert result.has_aspects() is False
