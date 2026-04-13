# tests/intents/plugins/test_exceptions.py
"""
Тесты обработки исключений в обработчиках плагинов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет поведение PluginRunContext при ошибках в обработчиках плагинов.
Декоратор @on принимает параметр ignore_exceptions, который определяет
стратегию обработки ошибок:

- ignore_exceptions=True: ошибка обработчика подавляется; при переданном
  log_coordinator пишется CRITICAL в Channel.error. Состояние плагина
  НЕ обновляется возвращённым значением (return не выполняется), но
  in-place мутации dict, произведённые до raise, остаются видны, так как
  dict — мутабельный объект и передаётся по ссылке.

- ignore_exceptions=False: ошибка обработчика пробрасывается наружу
  через emit_event(). Это прерывает выполнение действия и позволяет
  машине обработать ошибку на верхнем уровне.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

ignore_exceptions=True:
- Ошибка подавляется, emit_event() не выбрасывает исключение.
- При log_coordinator — одна запись critical + Channel.error на подавленный сбой.
- In-place мутация state до raise видна (before_error=True).
- Код после raise не выполняется (after_error остаётся False).

ignore_exceptions=False:
- RuntimeError пробрасывается из emit_event() с правильным сообщением.
- Кастомное исключение CustomPluginException пробрасывается с сохранением типа.
"""

import pytest

from action_machine.intents.logging.channel import Channel
from action_machine.intents.logging.level import Level
from action_machine.intents.logging.log_coordinator import LogCoordinator
from action_machine.intents.plugins.events import GlobalFinishEvent
from action_machine.intents.plugins.plugin_coordinator import PluginCoordinator
from action_machine.model.base_result import BaseResult
from tests.intents.logging.test_log_coordinator import RecordingLogger

from .conftest import (
    _TEST_ACTION_CLASS,
    _TEST_ACTION_NAME,
    _TEST_CONTEXT,
    _TEST_PARAMS,
    CounterPlugin,
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

    @pytest.mark.anyio
    async def test_suppressed_error_emits_critical_on_error_channel_parallel(self) -> None:
        """Все ignore=True → gather; сбой даёт CRITICAL с маской Channel.error."""
        plugin = IgnoredErrorPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()
        recording = RecordingLogger()
        log_coord = LogCoordinator(loggers=[recording])

        event = GlobalFinishEvent(
            action_class=_TEST_ACTION_CLASS,
            action_name=_TEST_ACTION_NAME,
            nest_level=1,
            context=_TEST_CONTEXT,
            params=_TEST_PARAMS,
            result=BaseResult(),
            duration_ms=0.0,
        )
        await plugin_ctx.emit_event(
            event,
            log_coordinator=log_coord,
            machine_name="TestMachine",
            mode="test",
        )

        assert len(recording.records) == 1
        rec = recording.records[0]
        assert rec["var"]["level"].mask == Level.critical
        assert rec["var"]["channels"].mask == Channel.error
        assert "on_error_handler" in rec["message"]
        assert "Ignored error" in rec["message"]
        assert "suppressed" in rec["message"].lower()

    @pytest.mark.anyio
    async def test_suppressed_error_emits_critical_sequential_path(self) -> None:
        """Смесь ignore True/False → последовательно; подавленный сбой логируется."""
        plugin = IgnoredErrorPlugin()
        counter = CounterPlugin()
        coordinator = PluginCoordinator(plugins=[plugin, counter])
        plugin_ctx = await coordinator.create_run_context()
        recording = RecordingLogger()
        log_coord = LogCoordinator(loggers=[recording])

        event = GlobalFinishEvent(
            action_class=_TEST_ACTION_CLASS,
            action_name=_TEST_ACTION_NAME,
            nest_level=1,
            context=_TEST_CONTEXT,
            params=_TEST_PARAMS,
            result=BaseResult(),
            duration_ms=0.0,
        )
        await plugin_ctx.emit_event(
            event,
            log_coordinator=log_coord,
            machine_name="TestMachine",
            mode="test",
        )

        assert len(recording.records) == 1
        assert recording.records[0]["var"]["channels"].mask == Channel.error
        assert plugin_ctx.get_plugin_state(counter)["count"] == 1


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
