# tests/compensate/test_compensate_metadata.py
"""
Тесты сборки метаданных компенсаторов через MetadataBuilder.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что декоратор @compensate правильно собирается в ClassMetadata:
- Компенсаторы извлекаются из vars(cls) (не наследуются).
- CompensatorMeta содержит method_name, target_aspect_name, description,
  method_ref и context_keys (из @context_requires).
- Валидации при сборке: привязка к существующему аспекту, целевой аспект
  должен быть regular, уникальность компенсатора для аспекта.
- API ClassMetadata: has_compensators(), get_compensator_for_aspect().
"""

from __future__ import annotations

import pytest

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth import ROLE_NONE, check_roles
from action_machine.compensate import compensate
from action_machine.context import Ctx, context_requires
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.meta_decorator import meta
from action_machine.metadata import MetadataBuilder

# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные базовые классы для тестов
# ═════════════════════════════════════════════════════════════════════════════


class EmptyParams(BaseParams):
    pass


class EmptyResult(BaseResult):
    pass


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorCollection — сборка компенсаторов
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorCollection:
    """Проверяет, что компенсаторы корректно собираются в ClassMetadata."""

    def test_single_compensator_collected(self) -> None:
        """
        Один компенсатор собирается в metadata.compensators.
        """

        @meta(description="Тестовое действие")
        @check_roles(ROLE_NONE)
        class MyAction(BaseAction[EmptyParams, EmptyResult]):

            @regular_aspect("Аспект")
            async def charge_aspect(self, params, state, box, connections):
                return {"txn_id": "123"}

            @compensate("charge_aspect", "Откат")
            async def rollback_compensate(self, params, state_before, state_after,
                                          box, connections, error):
                pass

            @summary_aspect("Саммари")
            async def summary(self, params, state, box, connections):
                return EmptyResult()

        metadata = MetadataBuilder.build(MyAction)
        assert metadata.has_compensators()
        assert len(metadata.compensators) == 1

        comp = metadata.compensators[0]
        assert comp.method_name == "rollback_compensate"
        assert comp.target_aspect_name == "charge_aspect"
        assert comp.description == "Откат"
        assert callable(comp.method_ref)
        assert comp.context_keys == frozenset()

    def test_compensator_with_context_requires(self) -> None:
        """
        Компенсатор с @context_requires: context_keys собираются.
        """

        @meta(description="Тестовое действие")
        @check_roles(ROLE_NONE)
        class MyAction(BaseAction[EmptyParams, EmptyResult]):

            @regular_aspect("Аспект")
            async def charge_aspect(self, params, state, box, connections):
                return {"txn_id": "123"}

            @compensate("charge_aspect", "Откат с контекстом")
            @context_requires(Ctx.User.user_id)
            async def rollback_with_context_compensate(self, params, state_before, state_after,
                                                       box, connections, error, ctx):
                pass

            @summary_aspect("Саммари")
            async def summary(self, params, state, box, connections):
                return EmptyResult()

        metadata = MetadataBuilder.build(MyAction)
        comp = metadata.compensators[0]
        assert comp.context_keys == frozenset({"user.user_id"})

    def test_has_compensators_returns_false_when_none(self) -> None:
        """
        has_compensators() возвращает False, если компенсаторов нет.
        """

        @meta(description="Тестовое действие")
        @check_roles(ROLE_NONE)
        class NoCompensateAction(BaseAction[EmptyParams, EmptyResult]):

            @regular_aspect("Аспект")
            async def charge_aspect(self, params, state, box, connections):
                return {"txn_id": "123"}

            @summary_aspect("Саммари")
            async def summary(self, params, state, box, connections):
                return EmptyResult()

        metadata = MetadataBuilder.build(NoCompensateAction)
        assert not metadata.has_compensators()
        assert len(metadata.compensators) == 0

    def test_compensator_not_inherited(self) -> None:
        """
        Компенсаторы не наследуются: дочерний Action без своих @compensate
        имеет пустой compensators.
        """

        @meta(description="Родитель")
        @check_roles(ROLE_NONE)
        class ParentAction(BaseAction[EmptyParams, EmptyResult]):

            @regular_aspect("Родительский аспект")
            async def parent_aspect(self, params, state, box, connections):
                return {}

            @compensate("parent_aspect", "Родительский компенсатор")
            async def parent_compensate(self, params, state_before, state_after,
                                        box, connections, error):
                pass

            @summary_aspect("Саммари")
            async def summary(self, params, state, box, connections):
                return EmptyResult()

        @meta(description="Дочерний")
        @check_roles(ROLE_NONE)
        class ChildAction(ParentAction):
            @regular_aspect("Дочерний аспект")
            async def child_aspect(self, params, state, box, connections):
                return {}

            @summary_aspect("Саммари дочерний")
            async def child_summary(self, params, state, box, connections):
                return EmptyResult()

        parent_meta = MetadataBuilder.build(ParentAction)
        child_meta = MetadataBuilder.build(ChildAction)

        assert len(parent_meta.compensators) == 1
        assert len(child_meta.compensators) == 0


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorValidation — валидации инвариантов
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorValidation:
    """Проверяет, что MetadataBuilder выбрасывает ошибки при нарушении инвариантов."""

    def test_target_aspect_not_exists(self) -> None:
        """
        Компенсатор привязан к несуществующему аспекту → ValueError.
        """

        with pytest.raises(ValueError, match="привязан к аспекту 'nonexistent', который не существует"):

            @meta(description="Тестовое действие")
            @check_roles(ROLE_NONE)
            class BadAction(BaseAction[EmptyParams, EmptyResult]):

                @regular_aspect("Существующий аспект")
                async def existing_aspect(self, params, state, box, connections):
                    return {}

                @compensate("nonexistent", "Компенсатор к несуществующему")
                async def bad_compensate(self, params, state_before, state_after,
                                         box, connections, error):
                    pass

                @summary_aspect("Саммари")
                async def summary(self, params, state, box, connections):
                    return EmptyResult()

            MetadataBuilder.build(BadAction)

    def test_target_aspect_is_summary(self) -> None:
        """
        Компенсатор привязан к summary-аспекту → ValueError.
        """
        with pytest.raises(ValueError, match="имеет тип 'summary'"):

            @meta(description="Тестовое действие")
            @check_roles(ROLE_NONE)
            class BadAction(BaseAction[EmptyParams, EmptyResult]):

                @summary_aspect("Саммари-аспект")
                async def summary_summary(self, params, state, box, connections):
                    return EmptyResult()

                @compensate("summary_summary", "Компенсатор к summary")
                async def bad_compensate(self, params, state_before, state_after,
                                         box, connections, error):
                    pass

            MetadataBuilder.build(BadAction)

    def test_duplicate_compensator_for_same_aspect(self) -> None:
        """
        Два компенсатора на один аспект → ValueError.
        """
        with pytest.raises(ValueError, match="имеет два компенсатора"):

            @meta(description="Тестовое действие")
            @check_roles(ROLE_NONE)
            class BadAction(BaseAction[EmptyParams, EmptyResult]):

                @regular_aspect("Целевой аспект")
                async def target_aspect(self, params, state, box, connections):
                    return {}

                @compensate("target_aspect", "Первый компенсатор")
                async def compensate1_compensate(self, params, state_before, state_after,
                                                 box, connections, error):
                    pass

                @compensate("target_aspect", "Второй компенсатор")
                async def compensate2_compensate(self, params, state_before, state_after,
                                                 box, connections, error):
                    pass

                @summary_aspect("Саммари")
                async def summary(self, params, state, box, connections):
                    return EmptyResult()

            MetadataBuilder.build(BadAction)


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorGetForAspect — API ClassMetadata
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorGetForAspect:
    """Проверяет методы доступа к компенсаторам в ClassMetadata."""

    def test_get_compensator_for_existing_aspect(self) -> None:
        """
        get_compensator_for_aspect() возвращает CompensatorMeta для существующего аспекта.
        """

        @meta(description="Тестовое действие")
        @check_roles(ROLE_NONE)
        class MyAction(BaseAction[EmptyParams, EmptyResult]):

            @regular_aspect("Первый аспект")
            async def first_aspect(self, params, state, box, connections):
                return {}

            @regular_aspect("Второй аспект")
            async def second_aspect(self, params, state, box, connections):
                return {}

            @compensate("first_aspect", "Компенсатор первого")
            async def comp_first_compensate(self, params, state_before, state_after,
                                            box, connections, error):
                pass

            @compensate("second_aspect", "Компенсатор второго")
            async def comp_second_compensate(self, params, state_before, state_after,
                                             box, connections, error):
                pass

            @summary_aspect("Саммари")
            async def summary(self, params, state, box, connections):
                return EmptyResult()

        metadata = MetadataBuilder.build(MyAction)
        comp_first = metadata.get_compensator_for_aspect("first_aspect")
        comp_second = metadata.get_compensator_for_aspect("second_aspect")
        comp_none = metadata.get_compensator_for_aspect("nonexistent")

        assert comp_first is not None
        assert comp_first.target_aspect_name == "first_aspect"
        assert comp_second is not None
        assert comp_second.target_aspect_name == "second_aspect"
        assert comp_none is None

    def test_get_compensator_for_aspect_without_compensator(self) -> None:
        """
        Для аспекта без компенсатора возвращается None.
        """

        @meta(description="Тестовое действие")
        @check_roles(ROLE_NONE)
        class MyAction(BaseAction[EmptyParams, EmptyResult]):

            @regular_aspect("С компенсатором")
            async def with_comp_aspect(self, params, state, box, connections):
                return {}

            @regular_aspect("Без компенсатора")
            async def without_comp_aspect(self, params, state, box, connections):
                return {}

            @compensate("with_comp_aspect", "Компенсатор")
            async def comp_compensate(self, params, state_before, state_after,
                                      box, connections, error):
                pass

            @summary_aspect("Саммари")
            async def summary(self, params, state, box, connections):
                return EmptyResult()

        metadata = MetadataBuilder.build(MyAction)
        assert metadata.get_compensator_for_aspect("with_comp_aspect") is not None
        assert metadata.get_compensator_for_aspect("without_comp_aspect") is None


# ═════════════════════════════════════════════════════════════════════════════
# TestCompensatorContextRequiresGateHost — проверка гейт-хоста
# ═════════════════════════════════════════════════════════════════════════════


class TestCompensatorContextRequiresGateHost:
    """
    Проверяет, что при использовании @context_requires на компенсаторе
    класс обязан наследовать ContextRequiresGateHost (BaseAction уже включает).
    """

    def test_context_requires_with_gate_host_works(self) -> None:
        """
        Компенсатор с @context_requires в классе, наследующем BaseAction,
        успешно собирается.
        """
        @meta(description="Тестовое действие")
        @check_roles(ROLE_NONE)
        class GoodAction(BaseAction[EmptyParams, EmptyResult]):

            @regular_aspect("Аспект")
            async def charge_aspect(self, params, state, box, connections):
                return {}

            @compensate("charge_aspect", "Откат")
            @context_requires(Ctx.User.user_id)
            async def rollback_compensate(self, params, state_before, state_after,
                                          box, connections, error, ctx):
                pass

            @summary_aspect("Саммари")
            async def summary(self, params, state, box, connections):
                return EmptyResult()

        metadata = MetadataBuilder.build(GoodAction)
        comp = metadata.compensators[0]
        assert comp.context_keys == frozenset({"user.user_id"})
