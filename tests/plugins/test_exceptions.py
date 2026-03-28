# tests/plugins/test_exceptions.py
"""
Тесты обработки исключений в обработчиках плагинов.

Проверяется:
- ignore_exceptions=True: ошибка обработчика подавляется молча,
  состояние плагина НЕ обновляется возвращённым значением (return
  не выполняется), но in-place мутации dict, произведённые до raise,
  остаются видны, так как dict — мутабельный объект.
- ignore_exceptions=False: ошибка обработчика пробрасывается наружу
  и прерывает выполнение.
- Кастомные исключения корректно пробрасываются при ignore_exceptions=False.

Все события отправляются через PluginRunContext.emit_event(),
создаваемый через PluginCoordinator.create_run_context().
"""

import pytest

from action_machine.aspects.summary_aspect import summary_aspect
from action_machine.auth.check_roles import CheckRoles
from action_machine.context.context import Context
from action_machine.core.base_action import BaseAction
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.plugins.decorators import on
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_coordinator import PluginCoordinator
from action_machine.plugins.plugin_event import PluginEvent

# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные классы
# ─────────────────────────────────────────────────────────────────────────────

@CheckRoles(CheckRoles.NONE, desc="")
class DummyAction(BaseAction[BaseParams, BaseResult]):
    """Минимальное действие для тестов."""

    @summary_aspect("dummy")
    async def summary(self, params, state, box, connections):
        return BaseResult()


class IgnoredErrorPlugin(Plugin):
    """
    Плагин с обработчиком, который падает с ignore_exceptions=True.

    Обработчик мутирует state["before_error"] = True до raise.
    Поскольку state — dict (мутабельный объект), in-place мутация
    сохраняется даже при ошибке. Однако return не выполняется,
    поэтому _run_single_handler не вызывает присвоение нового state.
    На практике, так как это тот же объект dict, мутация видна.

    state["after_error"] остаётся False, так как код после raise
    не выполняется.
    """

    async def get_initial_state(self) -> dict:
        return {"before_error": False, "after_error": False}

    @on("global_finish", ".*", ignore_exceptions=True)
    async def failing_handler(self, state: dict, event: PluginEvent) -> dict:
        state["before_error"] = True
        raise RuntimeError("Ignored error")
        # state["after_error"] = True  # не выполнится


class PropagatedErrorPlugin(Plugin):
    """Плагин с обработчиком, который падает с ignore_exceptions=False."""

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def strict_handler(self, state: dict, event: PluginEvent) -> dict:
        raise RuntimeError("Strict error must propagate")


class CustomException(Exception):
    """Кастомное исключение для тестов."""
    pass


class CustomExceptionPlugin(Plugin):
    """Плагин с обработчиком, выбрасывающим кастомное исключение."""

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def custom_handler(self, state: dict, event: PluginEvent) -> dict:
        raise CustomException("Custom plugin error")


class SuccessPlugin(Plugin):
    """Плагин с успешным обработчиком (для проверки совместной работы)."""

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def success_handler(self, state: dict, event: PluginEvent) -> dict:
        state["count"] += 1
        return state


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def _make_empty_factory() -> DependencyFactory:
    # removed: gate not needed
    # removed: freeze not needed
    return DependencyFactory(())


async def _emit_global_finish(plugin_ctx):
    """Отправляет событие global_finish через контекст."""
    await plugin_ctx.emit_event(
        event_name="global_finish",
        action=DummyAction(),
        params=BaseParams(),
        state_aspect=None,
        is_summary=False,
        result=None,
        duration=1.0,
        factory=_make_empty_factory(),
        context=Context(),
        nest_level=0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Тесты
# ─────────────────────────────────────────────────────────────────────────────

class TestPluginCoordinatorExceptions:
    """Тесты обработки исключений в обработчиках плагинов."""

    @pytest.mark.anyio
    async def test_ignore_exceptions_true(self):
        """
        ignore_exceptions=True: ошибка обработчика подавляется молча.

        Поскольку state — dict (мутабельный объект), in-place мутация
        state["before_error"] = True, произведённая до raise, остаётся
        видна. Код после raise не выполняется, поэтому
        state["after_error"] остаётся False.
        """
        plugin = IgnoredErrorPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Не должно быть исключения
        await _emit_global_finish(plugin_ctx)

        state = plugin_ctx.get_plugin_state(plugin)
        # Мутация до raise видна (dict мутируется in-place)
        assert state["before_error"] is True
        # Код после raise не выполнился
        assert state["after_error"] is False

    @pytest.mark.anyio
    async def test_ignore_exceptions_false_propagates(self):
        """
        ignore_exceptions=False: ошибка обработчика пробрасывается наружу.
        """
        plugin = PropagatedErrorPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        with pytest.raises(RuntimeError, match="Strict error must propagate"):
            await _emit_global_finish(plugin_ctx)

    @pytest.mark.anyio
    async def test_ignore_exceptions_with_custom_exception(self):
        """
        ignore_exceptions=False с кастомным исключением: исключение
        пробрасывается с правильным типом.
        """
        plugin = CustomExceptionPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        with pytest.raises(CustomException, match="Custom plugin error"):
            await _emit_global_finish(plugin_ctx)
