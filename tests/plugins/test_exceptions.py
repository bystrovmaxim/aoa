# tests/plugins/test_exceptions.py
"""
Тесты обработки исключений в обработчиках плагинов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет поведение PluginRunContext при ошибках в обработчиках плагинов.
Декоратор @on принимает параметр ignore_exceptions, который определяет
стратегию обработки ошибок:

- ignore_exceptions=True: ошибка обработчика подавляется молча.
  Состояние плагина НЕ обновляется возвращённым значением (return
  не выполняется), но in-place мутации dict, произведённые до raise,
  остаются видны, так как dict — мутабельный объект и передаётся
  по ссылке.

- ignore_exceptions=False: ошибка обработчика пробрасывается наружу
  через emit_event(). Это прерывает выполнение действия и позволяет
  машине обработать ошибку на верхнем уровне.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

ignore_exceptions=True:
- Ошибка подавляется, emit_event() не выбрасывает исключение.
- In-place мутация state до raise видна (before_error=True).
- Код после raise не выполняется (after_error остаётся False).

ignore_exceptions=False:
- RuntimeError пробрасывается из emit_event() с правильным сообщением.
- Кастомное исключение CustomPluginException пробрасывается с сохранением типа.
"""

import pytest

from action_machine.plugins.plugin_coordinator import PluginCoordinator

from .conftest import (
    CustomExceptionPlugin,
    CustomPluginError,
    IgnoredErrorPlugin,
    PropagatedErrorPlugin,
    emit_global_finish,
)


class TestIgnoreExceptionsTrue:
    """Тесты поведения при ignore_exceptions=True — ошибки подавляются."""

    @pytest.mark.anyio
    async def test_error_suppressed_no_exception(self):
        """
        IgnoredErrorPlugin выбрасывает RuntimeError с ignore_exceptions=True.
        emit_event() завершается без исключения — ошибка подавлена.
        """
        # Arrange — плагин с падающим обработчиком (ignore=True)
        plugin = IgnoredErrorPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act + Assert — не должно быть исключения
        await emit_global_finish(plugin_ctx)

    @pytest.mark.anyio
    async def test_in_place_mutation_before_raise_visible(self):
        """
        IgnoredErrorPlugin мутирует state["before_error"]=True до raise.
        Поскольку state — dict (мутабельный объект, передаётся по ссылке),
        in-place мутация остаётся видна даже при подавленной ошибке.
        """
        # Arrange — плагин, мутирующий state до raise
        plugin = IgnoredErrorPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — событие обрабатывается, ошибка подавляется
        await emit_global_finish(plugin_ctx)

        # Assert — мутация до raise видна
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["before_error"] is True

    @pytest.mark.anyio
    async def test_code_after_raise_not_executed(self):
        """
        IgnoredErrorPlugin: код после raise не выполняется.
        state["after_error"] остаётся False (начальное значение).
        """
        # Arrange — плагин с кодом после raise (который не выполнится)
        plugin = IgnoredErrorPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — событие обрабатывается
        await emit_global_finish(plugin_ctx)

        # Assert — код после raise не выполнился
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["after_error"] is False


class TestIgnoreExceptionsFalse:
    """Тесты поведения при ignore_exceptions=False — ошибки пробрасываются."""

    @pytest.mark.anyio
    async def test_runtime_error_propagates(self):
        """
        PropagatedErrorPlugin выбрасывает RuntimeError с ignore_exceptions=False.
        Ошибка пробрасывается из emit_event() с правильным сообщением.
        """
        # Arrange — плагин с критическим обработчиком
        plugin = PropagatedErrorPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act + Assert — RuntimeError пробрасывается
        with pytest.raises(RuntimeError, match="Strict error must propagate"):
            await emit_global_finish(plugin_ctx)

    @pytest.mark.anyio
    async def test_custom_exception_preserves_type(self):
        """
        CustomExceptionPlugin выбрасывает CustomPluginException.
        Тип кастомного исключения сохраняется при пробросе —
        вызывающий код может поймать конкретный тип.
        """
        # Arrange — плагин с кастомным исключением
        plugin = CustomExceptionPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act + Assert — CustomPluginException пробрасывается с сообщением
        with pytest.raises(CustomPluginError, match="Custom plugin error"):
            await emit_global_finish(plugin_ctx)
