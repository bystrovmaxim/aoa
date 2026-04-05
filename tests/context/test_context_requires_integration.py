# tests/context/test_context_requires_integration.py
"""
Интеграционные тесты @context_requires — полный прогон Action через
TestBench с проверкой передачи ContextView в аспекты и обработчики ошибок.

Action создаются внутри тестов, потому что содержат специфичную
логику чтения ctx и записи в result — используются только здесь.
"""

import pytest
from pydantic import Field

from action_machine.aspects.regular_aspect import regular_aspect
from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import check_roles
from action_machine.auth.constants import ROLE_NONE
from action_machine.checkers.result_string_checker import result_string
from action_machine.context.context_requires_decorator import context_requires
from action_machine.context.ctx_constants import Ctx
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.core.exceptions import ContextAccessError
from action_machine.core.meta_decorator import meta
from action_machine.on_error.on_error_decorator import on_error
from action_machine.testing import TestBench

# ═════════════════════════════════════════════════════════════════════════════
# Тестовые модели Params и Result
# ═════════════════════════════════════════════════════════════════════════════


class _IntegrationParams(BaseParams):
    """Параметры для интеграционных тестов context_requires."""
    name: str = Field(description="Имя для тестирования")


class _IntegrationResult(BaseResult):
    """Результат для интеграционных тестов context_requires."""
    message: str = Field(description="Сообщение результата")


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые Action
# ═════════════════════════════════════════════════════════════════════════════


@meta(description="Action с аспектом, читающим user_id из контекста")
@check_roles(ROLE_NONE)
class _CtxReadAction(BaseAction[_IntegrationParams, _IntegrationResult]):
    """Аспект с @context_requires читает user_id и записывает в результат."""

    @regular_aspect("Чтение контекста")
    @result_string("ctx_user_id", required=True)
    @context_requires(Ctx.User.user_id)
    async def read_ctx_aspect(self, params, state, box, connections, ctx):
        user_id = ctx.get(Ctx.User.user_id)
        return {"ctx_user_id": str(user_id)}

    @summary_aspect("Формирование результата")
    async def build_summary(self, params, state, box, connections):
        return _IntegrationResult(message=f"user={state['ctx_user_id']}")


@meta(description="Action без @context_requires — стандартная сигнатура")
@check_roles(ROLE_NONE)
class _NoCtxAction(BaseAction[_IntegrationParams, _IntegrationResult]):
    """Аспект без @context_requires работает с 5 параметрами как раньше."""

    @summary_aspect("Простой результат")
    async def build_summary(self, params, state, box, connections):
        return _IntegrationResult(message=f"hello {params.name}")


@meta(description="Action с аспектом, обращающимся к незапрошенному полю")
@check_roles(ROLE_NONE)
class _CtxAccessViolationAction(BaseAction[_IntegrationParams, _IntegrationResult]):
    """Аспект запрашивает user.user_id, но обращается к user.roles — ContextAccessError."""

    @regular_aspect("Нарушение доступа")
    @context_requires(Ctx.User.user_id)
    async def violate_aspect(self, params, state, box, connections, ctx):
        # Обращение к незапрошенному полю — должно бросить ContextAccessError
        ctx.get(Ctx.User.roles)
        return {}

    @summary_aspect("Итог")
    async def build_summary(self, params, state, box, connections):
        return _IntegrationResult(message="should not reach")


@meta(description="Action с обработчиком ошибок, читающим контекст")
@check_roles(ROLE_NONE)
class _OnErrorCtxAction(BaseAction[_IntegrationParams, _IntegrationResult]):
    """Аспект бросает ValueError, обработчик с @context_requires читает user_id."""

    @regular_aspect("Бросает ошибку")
    async def failing_aspect(self, params, state, box, connections):
        raise ValueError("test error")

    @summary_aspect("Итог")
    async def build_summary(self, params, state, box, connections):
        return _IntegrationResult(message="should not reach")

    @on_error(ValueError, description="Обработка с контекстом")
    @context_requires(Ctx.User.user_id)
    async def handle_on_error(self, params, state, box, connections, error, ctx):
        user_id = ctx.get(Ctx.User.user_id)
        return _IntegrationResult(message=f"error handled by {user_id}")


@meta(description="Action с обработчиком ошибок без @context_requires")
@check_roles(ROLE_NONE)
class _OnErrorNoCtxAction(BaseAction[_IntegrationParams, _IntegrationResult]):
    """Аспект бросает ValueError, обработчик без @context_requires — 6 параметров."""

    @regular_aspect("Бросает ошибку")
    async def failing_aspect(self, params, state, box, connections):
        raise ValueError("test error")

    @summary_aspect("Итог")
    async def build_summary(self, params, state, box, connections):
        return _IntegrationResult(message="should not reach")

    @on_error(ValueError, description="Обработка без контекста")
    async def handle_on_error(self, params, state, box, connections, error):
        return _IntegrationResult(message=f"error: {error}")


@meta(description="Action с summary, читающим контекст")
@check_roles(ROLE_NONE)
class _SummaryCtxAction(BaseAction[_IntegrationParams, _IntegrationResult]):
    """Summary-аспект с @context_requires читает hostname."""

    @summary_aspect("Результат с контекстом")
    @context_requires(Ctx.Runtime.hostname)
    async def build_summary(self, params, state, box, connections, ctx):
        hostname = ctx.get(Ctx.Runtime.hostname)
        return _IntegrationResult(message=f"host={hostname}")


# ═════════════════════════════════════════════════════════════════════════════
# Тесты
# ═════════════════════════════════════════════════════════════════════════════


class TestAspectWithContextRequires:
    """Аспект с @context_requires получает ContextView и читает данные."""

    @pytest.mark.asyncio
    async def test_reads_user_id_from_context(self) -> None:
        # Arrange — bench с пользователем test_agent
        bench = TestBench().with_user(user_id="test_agent")
        params = _IntegrationParams(name="test")

        # Act — полный прогон Action, аспект читает user_id через ctx
        result = await bench.run(_CtxReadAction(), params, rollup=False)

        # Assert — user_id из контекста попал в результат
        assert result.message == "user=test_agent"


class TestAspectWithoutContextRequires:
    """Аспект без @context_requires работает со стандартной сигнатурой."""

    @pytest.mark.asyncio
    async def test_standard_five_params(self) -> None:
        # Arrange — обычный bench
        bench = TestBench()
        params = _IntegrationParams(name="world")

        # Act — Action без @context_requires
        result = await bench.run(_NoCtxAction(), params, rollup=False)

        # Assert — аспект отработал с 5 параметрами
        assert result.message == "hello world"


class TestContextAccessViolation:
    """Обращение к незапрошенному полю пробрасывает ContextAccessError."""

    @pytest.mark.asyncio
    async def test_access_to_unregistered_key_raises(self) -> None:
        # Arrange — bench, Action обращается к user.roles, но запросил только user.user_id
        bench = TestBench().with_user(user_id="u1", roles=["admin"])
        params = _IntegrationParams(name="test")

        # Act / Assert — ContextAccessError пробрасывается наружу
        with pytest.raises(ContextAccessError) as exc_info:
            await bench.run(_CtxAccessViolationAction(), params, rollup=False)

        # Assert — ошибка указывает на запрошенный ключ
        assert exc_info.value.key == "user.roles"


class TestOnErrorWithContextRequires:
    """Обработчик ошибок с @context_requires получает свой ContextView."""

    @pytest.mark.asyncio
    async def test_error_handler_reads_context(self) -> None:
        # Arrange — bench с пользователем error_handler_user
        bench = TestBench().with_user(user_id="error_handler_user")
        params = _IntegrationParams(name="test")

        # Act — аспект бросает ValueError, обработчик читает user_id через ctx
        result = await bench.run(_OnErrorCtxAction(), params, rollup=False)

        # Assert — обработчик прочитал user_id из контекста
        assert result.message == "error handled by error_handler_user"


class TestOnErrorWithoutContextRequires:
    """Обработчик ошибок без @context_requires — стандартная сигнатура."""

    @pytest.mark.asyncio
    async def test_error_handler_standard_six_params(self) -> None:
        # Arrange
        bench = TestBench()
        params = _IntegrationParams(name="test")

        # Act — обработчик без контекста, 6 параметров
        result = await bench.run(_OnErrorNoCtxAction(), params, rollup=False)

        # Assert — обработчик отработал
        assert result.message == "error: test error"


class TestSummaryWithContextRequires:
    """Summary-аспект с @context_requires получает ContextView."""

    @pytest.mark.asyncio
    async def test_summary_reads_hostname(self) -> None:
        # Arrange — bench с runtime hostname
        bench = TestBench().with_runtime(hostname="prod-01")
        params = _IntegrationParams(name="test")

        # Act — summary читает hostname через ctx
        result = await bench.run(_SummaryCtxAction(), params, rollup=False)

        # Assert — hostname из контекста попал в результат
        assert result.message == "host=prod-01"


class TestBoxContextNotAccessible:
    """ToolsBox не предоставляет публичного доступа к контексту."""

    @pytest.mark.asyncio
    async def test_box_has_no_context_property(self) -> None:
        # Arrange — Action, проверяющий отсутствие box.context

        @meta(description="Проверка отсутствия box.context")
        @check_roles(ROLE_NONE)
        class _BoxCheckAction(BaseAction[BaseParams, BaseResult]):
            @summary_aspect("Проверка")
            async def check_summary(self, params, state, box, connections):
                # box.context не должен существовать как публичный атрибут
                has_context = hasattr(box, "context")
                result = BaseResult()
                result["has_context"] = has_context
                return result

        bench = TestBench()
        params = BaseParams()

        # Act
        result = await bench.run(_BoxCheckAction(), params, rollup=False)

        # Assert — box.context недоступен
        assert result["has_context"] is False
