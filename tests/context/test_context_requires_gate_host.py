# tests/context/test_context_requires_gate_host.py
"""
Тесты гейтхоста ContextRequiresGateHost — проверка согласованности
декоратора @context_requires с сигнатурой метода и наличием гейтхоста
в MRO класса.

АРХИТЕКТУРА ТЕСТОВ
------------------
Рабочие Action (с BaseAction) определяются внутри тестов, потому что
они проверяют специфичные комбинации декораторов и гейтхостов.

Намеренно сломанные классы (без нужного гейтхоста, с неверной сигнатурой)
создаются внутри тестов, потому что они заведомо невалидны и не могут
быть частью рабочей доменной модели.

ПРОВЕРЯЕМЫЕ ИНВАРИАНТЫ
-----------------------
1. @context_requires + 6 параметров → context_keys записываются в AspectMeta.
2. Без @context_requires + 5 параметров → context_keys = frozenset().
3. @context_requires + 5 параметров → TypeError (несогласованность).
4. Без @context_requires + 6 параметров → TypeError (лишний параметр).
5. То же для @on_error (6/7 параметров).
6. Класс без ContextRequiresGateHost + @context_requires → TypeError.
7. Смешанные аспекты (с и без @context_requires) — корректны.
"""

import pytest

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import check_roles
from action_machine.auth.constants import ROLE_NONE
from action_machine.auth.role_gate_host import RoleGateHost
from action_machine.context.context_requires_decorator import context_requires
from action_machine.context.ctx_constants import Ctx
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.meta_decorator import meta
from action_machine.core.meta_gate_hosts import ActionMetaGateHost
from action_machine.metadata.builder import MetadataBuilder
from action_machine.on_error.on_error_decorator import on_error
from action_machine.on_error.on_error_gate_host import OnErrorGateHost


class TestAspectWithContextRequires:
    """Аспект с @context_requires и 6 параметрами — корректен."""

    def test_regular_aspect_with_ctx_six_params(self) -> None:
        """
        Сценарий: regular-аспект с @context_requires(Ctx.User.user_id)
        и 6 параметрами (self, params, state, box, connections, ctx).
        MetadataBuilder должен записать context_keys в AspectMeta.
        """

        # Arrange — Action с regular-аспектом, у которого @context_requires и 6 параметров

        @meta(description="Тест context_requires на regular_aspect")
        @check_roles(ROLE_NONE)
        class ValidCtxAction(BaseAction[BaseParams, BaseResult]):
            @regular_aspect("С контекстом")
            @context_requires(Ctx.User.user_id)
            async def check_aspect(self, params, state, box, connections, ctx):
                return {}

            @summary_aspect("Итог")
            async def build_summary(self, params, state, box, connections):
                return BaseResult()

        # Act — сборка метаданных не бросает исключение
        metadata = MetadataBuilder.build(ValidCtxAction)

        # Assert — context_keys записаны в AspectMeta
        regular_aspects = metadata.get_regular_aspects()
        assert len(regular_aspects) == 1
        assert regular_aspects[0].context_keys == frozenset({"user.user_id"})

    def test_summary_aspect_with_ctx_six_params(self) -> None:
        """
        Сценарий: summary-аспект с @context_requires(Ctx.User.user_id,
        Ctx.Request.trace_id) и 6 параметрами.
        MetadataBuilder должен записать оба ключа в context_keys.
        """

        # Arrange — Action с summary-аспектом с @context_requires и 6 параметрами

        @meta(description="Тест context_requires на summary_aspect")
        @check_roles(ROLE_NONE)
        class ValidSummaryCtxAction(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("С контекстом")
            @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
            async def build_summary(self, params, state, box, connections, ctx):
                return BaseResult()

        # Act
        metadata = MetadataBuilder.build(ValidSummaryCtxAction)

        # Assert — context_keys на summary-аспекте
        summary = metadata.get_summary_aspect()
        assert summary is not None
        assert summary.context_keys == frozenset({"user.user_id", "request.trace_id"})


class TestAspectWithoutContextRequires:
    """Аспект без @context_requires и 5 параметрами — корректен."""

    def test_regular_aspect_without_ctx_five_params(self) -> None:
        """
        Сценарий: стандартный regular-аспект без @context_requires,
        5 параметров (self, params, state, box, connections).
        context_keys должен быть пустым frozenset.
        """

        # Arrange — стандартный Action без @context_requires

        @meta(description="Тест без context_requires")
        @check_roles(ROLE_NONE)
        class NoCtxAction(BaseAction[BaseParams, BaseResult]):
            @regular_aspect("Без контекста")
            async def process_aspect(self, params, state, box, connections):
                return {}

            @summary_aspect("Итог")
            async def build_summary(self, params, state, box, connections):
                return BaseResult()

        # Act
        metadata = MetadataBuilder.build(NoCtxAction)

        # Assert — context_keys пустой frozenset
        regular_aspects = metadata.get_regular_aspects()
        assert len(regular_aspects) == 1
        assert regular_aspects[0].context_keys == frozenset()


class TestMismatchDecoratorAndSignature:
    """Несогласованность @context_requires и количества параметров — ошибка."""

    def test_context_requires_but_five_params_raises(self) -> None:
        """
        Сценарий: @context_requires есть, но параметров 5 (нет ctx).
        Декоратор @regular_aspect должен выбросить TypeError.
        """

        # Arrange / Act / Assert — @context_requires есть, но параметров 5 (нет ctx)
        with pytest.raises(TypeError, match="6 параметров"):
            @regular_aspect("Сломанный")
            @context_requires(Ctx.User.user_id)
            async def broken_aspect(self, params, state, box, connections):
                return {}

    def test_no_context_requires_but_six_params_raises(self) -> None:
        """
        Сценарий: @context_requires нет, но параметров 6 (лишний ctx).
        Декоратор @regular_aspect должен выбросить TypeError.
        """

        # Arrange / Act / Assert — @context_requires нет, но параметров 6 (лишний ctx)
        with pytest.raises(TypeError, match="5 параметров"):
            @regular_aspect("Сломанный")
            async def broken_aspect(self, params, state, box, connections, ctx):
                return {}

    def test_summary_context_requires_but_five_params_raises(self) -> None:
        """
        Сценарий: summary с @context_requires, но 5 параметров.
        Декоратор @summary_aspect должен выбросить TypeError.
        """

        # Arrange / Act / Assert — summary с @context_requires, но 5 параметров
        with pytest.raises(TypeError, match="6 параметров"):
            @summary_aspect("Сломанный")
            @context_requires(Ctx.User.user_id)
            async def broken_summary(self, params, state, box, connections):
                return BaseResult()

    def test_summary_no_context_requires_but_six_params_raises(self) -> None:
        """
        Сценарий: summary без @context_requires, но 6 параметров.
        Декоратор @summary_aspect должен выбросить TypeError.
        """

        # Arrange / Act / Assert — summary без @context_requires, но 6 параметров
        with pytest.raises(TypeError, match="5 параметров"):
            @summary_aspect("Сломанный")
            async def broken_summary(self, params, state, box, connections, ctx):
                return BaseResult()


class TestOnErrorWithContextRequires:
    """Обработчик ошибок с @context_requires и 7 параметрами — корректен."""

    def test_on_error_with_ctx_seven_params(self) -> None:
        """
        Сценарий: обработчик ошибок с @context_requires(Ctx.User.user_id)
        и 7 параметрами (self, params, state, box, connections, error, ctx).
        MetadataBuilder должен записать context_keys в OnErrorMeta.
        """

        # Arrange — Action с обработчиком ошибок с @context_requires

        @meta(description="Тест on_error с context_requires")
        @check_roles(ROLE_NONE)
        class ErrorCtxAction(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("Итог")
            async def build_summary(self, params, state, box, connections):
                return BaseResult()

            @on_error(ValueError, description="С контекстом")
            @context_requires(Ctx.User.user_id)
            async def handle_on_error(self, params, state, box, connections, error, ctx):
                return BaseResult()

        # Act
        metadata = MetadataBuilder.build(ErrorCtxAction)

        # Assert — context_keys записаны в OnErrorMeta
        assert len(metadata.error_handlers) == 1
        assert metadata.error_handlers[0].context_keys == frozenset({"user.user_id"})

    def test_on_error_without_ctx_six_params(self) -> None:
        """
        Сценарий: обработчик ошибок без @context_requires,
        стандартные 6 параметров (self, params, state, box, connections, error).
        context_keys должен быть пустым frozenset.
        """

        # Arrange — обработчик ошибок без @context_requires, стандартные 6 параметров

        @meta(description="Тест on_error без context_requires")
        @check_roles(ROLE_NONE)
        class ErrorNoCtxAction(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("Итог")
            async def build_summary(self, params, state, box, connections):
                return BaseResult()

            @on_error(ValueError, description="Без контекста")
            async def handle_on_error(self, params, state, box, connections, error):
                return BaseResult()

        # Act
        metadata = MetadataBuilder.build(ErrorNoCtxAction)

        # Assert — context_keys пустой frozenset
        assert len(metadata.error_handlers) == 1
        assert metadata.error_handlers[0].context_keys == frozenset()


class TestOnErrorMismatchSignature:
    """Несогласованность @context_requires и сигнатуры обработчика ошибок."""

    def test_on_error_context_requires_but_six_params_raises(self) -> None:
        """
        Сценарий: @on_error с @context_requires, но 6 параметров (нет ctx).
        Декоратор @on_error должен выбросить TypeError.
        """

        # Arrange / Act / Assert — @context_requires есть, но 6 параметров (нет ctx)
        with pytest.raises(TypeError, match="7 параметров"):
            @on_error(ValueError, description="Сломанный")
            @context_requires(Ctx.User.user_id)
            async def broken_on_error(self, params, state, box, connections, error):
                return BaseResult()

    def test_on_error_no_context_requires_but_seven_params_raises(self) -> None:
        """
        Сценарий: @on_error без @context_requires, но 7 параметров (лишний ctx).
        Декоратор @on_error должен выбросить TypeError.
        """

        # Arrange / Act / Assert — нет @context_requires, но 7 параметров
        with pytest.raises(TypeError, match="6 параметров"):
            @on_error(ValueError, description="Сломанный")
            async def broken_on_error(self, params, state, box, connections, error, ctx):
                return BaseResult()


class TestGateHostRequired:
    """Класс без ContextRequiresGateHost не может иметь @context_requires."""

    def test_class_without_gate_host_raises(self) -> None:
        """
        Сценарий: класс содержит аспект с @context_requires, но НЕ наследует
        ContextRequiresGateHost. MetadataBuilder.build() должен выбросить
        TypeError с упоминанием ContextRequiresGateHost.

        Класс наследует все необходимые гейт-хосты (ActionMetaGateHost,
        RoleGateHost, AspectGateHost, OnErrorGateHost) для прохождения
        предшествующих валидаций, но намеренно НЕ наследует
        ContextRequiresGateHost. Декораторы @meta и @check_roles
        добавлены для прохождения валидации обязательных метаданных.
        """

        # Arrange — класс со ВСЕМИ гейт-хостами КРОМЕ ContextRequiresGateHost

        @meta(description="Тест без ContextRequiresGateHost")
        @check_roles(ROLE_NONE)
        class NoContextGateHostAction(
            ActionMetaGateHost,
            RoleGateHost,
            AspectGateHost,
            OnErrorGateHost,
        ):
            @regular_aspect("С контекстом")
            @context_requires(Ctx.User.user_id)
            async def check_aspect(self, params, state, box, connections, ctx):
                return {}

            @summary_aspect("Итог")
            async def build_summary(self, params, state, box, connections):
                return BaseResult()

        # Act / Assert — MetadataBuilder обнаруживает отсутствие ContextRequiresGateHost
        with pytest.raises(TypeError, match="ContextRequiresGateHost"):
            MetadataBuilder.build(NoContextGateHostAction)


class TestMixedAspects:
    """Action с аспектами: часть с @context_requires, часть без."""

    def test_mixed_aspects_valid(self) -> None:
        """
        Сценарий: два regular-аспекта — один с @context_requires,
        другой без. Оба корректны; context_keys записываются
        только для аспекта с декоратором.
        """

        # Arrange — два regular-аспекта: один с контекстом, другой без

        @meta(description="Смешанные аспекты")
        @check_roles(ROLE_NONE)
        class MixedAction(BaseAction[BaseParams, BaseResult]):
            @regular_aspect("С контекстом")
            @context_requires(Ctx.User.user_id)
            async def with_ctx_aspect(self, params, state, box, connections, ctx):
                return {}

            @regular_aspect("Без контекста")
            async def without_ctx_aspect(self, params, state, box, connections):
                return {}

            @summary_aspect("Итог")
            async def build_summary(self, params, state, box, connections):
                return BaseResult()

        # Act
        metadata = MetadataBuilder.build(MixedAction)

        # Assert — у первого аспекта есть context_keys, у второго — нет
        regulars = metadata.get_regular_aspects()
        assert len(regulars) == 2

        with_ctx = [a for a in regulars if a.context_keys]
        without_ctx = [a for a in regulars if not a.context_keys]

        assert len(with_ctx) == 1
        assert len(without_ctx) == 1
        assert with_ctx[0].context_keys == frozenset({"user.user_id"})
        assert without_ctx[0].context_keys == frozenset()
