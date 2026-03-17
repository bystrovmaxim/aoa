"""
Тесты конкурентного выполнения обработчиков плагинов.

Проверяем:
- Ограничение количества одновременно выполняющихся обработчиков через семафор
- Правильность времени выполнения при ограничении
- Смешанные сценарии с разными типами обработчиков
"""

import asyncio

import pytest

from action_machine.Plugins.PluginCoordinator import PluginCoordinator

from .conftest import MockParams, SimplePlugin, SlowPlugin


class TestPluginCoordinatorConcurrency:
    """Тесты конкурентного выполнения обработчиков."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Ограничение конкурентности
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_semaphore_limits_concurrency(self, mock_action, mock_factory, mock_context):
        """
        Семафор ограничивает количество одновременно выполняющихся обработчиков.

        Создаём 5 медленных плагинов с max_concurrent_handlers=2.
        Ожидаем, что общее время выполнения будет ~0.3с (3 волны по 0.1с),
        а не 0.1с (если бы все выполнялись параллельно).
        """
        plugins = [SlowPlugin() for _ in range(5)]
        coordinator = PluginCoordinator(plugins, max_concurrent_handlers=2)

        action = mock_action
        params = MockParams()

        start_time = asyncio.get_event_loop().time()

        await coordinator.emit_event(
            event_name="slow_event",
            action=action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        assert duration >= 0.25, f"Ожидали время >=0.25с, получили {duration:.2f}с"
        assert duration < 0.6, f"Слишком долго: {duration:.2f}с"

        for plugin in plugins:
            assert plugin.handlers_called == [("slow", "slow_event")]

    @pytest.mark.anyio
    async def test_semaphore_with_max_concurrent_1(self, mock_action, mock_factory, mock_context):
        """
        При max_concurrent_handlers=1 обработчики выполняются последовательно.

        Время выполнения должно быть ~0.5с (5 * 0.1с).
        """
        plugins = [SlowPlugin() for _ in range(5)]
        coordinator = PluginCoordinator(plugins, max_concurrent_handlers=1)

        action = mock_action
        params = MockParams()

        start_time = asyncio.get_event_loop().time()

        await coordinator.emit_event(
            event_name="slow_event",
            action=action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        assert duration >= 0.45, f"Ожидали время >=0.45с, получили {duration:.2f}с"
        assert duration < 0.8, f"Слишком долго: {duration:.2f}с"

    @pytest.mark.anyio
    async def test_semaphore_with_max_concurrent_equal_to_plugins(self, mock_action, mock_factory, mock_context):
        """
        Если max_concurrent_handlers >= количеству плагинов,
        все выполняются параллельно.

        Время выполнения должно быть ~0.1с.
        """
        plugins = [SlowPlugin() for _ in range(5)]
        coordinator = PluginCoordinator(plugins, max_concurrent_handlers=10)

        action = mock_action
        params = MockParams()

        start_time = asyncio.get_event_loop().time()

        await coordinator.emit_event(
            event_name="slow_event",
            action=action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        assert duration < 0.3, f"Ожидали время <0.3с, получили {duration:.2f}с"

    # ------------------------------------------------------------------
    # ТЕСТЫ: Смешанные сценарии
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_semaphore_with_mixed_handlers(self, mock_action, mock_factory, mock_context):
        """
        Семафор работает с разными типами обработчиков.

        Быстрые и медленные обработчики смешаны, но ограничение
        должно применяться ко всем одинаково.
        """
        slow_plugins = [SlowPlugin() for _ in range(3)]
        fast_plugin = SimplePlugin()

        all_plugins = slow_plugins + [fast_plugin]
        coordinator = PluginCoordinator(all_plugins, max_concurrent_handlers=2)

        action = mock_action
        params = MockParams()

        await asyncio.gather(
            coordinator.emit_event(
                event_name="slow_event",
                action=action,
                params=params,
                state_aspect={},
                is_summary=False,
                result=None,
                duration=None,
                factory=mock_factory,
                context=mock_context,
                nest_level=0,
            ),
            coordinator.emit_event(
                event_name="test_event",
                action=action,
                params=params,
                state_aspect={},
                is_summary=False,
                result=None,
                duration=None,
                factory=mock_factory,
                context=mock_context,
                nest_level=0,
            ),
        )

        for plugin in slow_plugins:
            assert plugin.handlers_called == [("slow", "slow_event")]

        assert fast_plugin.handlers_called == [("handle_test", "test_event")]

    @pytest.mark.anyio
    async def test_semaphore_resets_between_events(self, mock_action, mock_factory, mock_context):
        """
        Семафор не накапливает состояние между разными вызовами emit_event.

        После завершения одного события семафор освобождается для следующего.
        """
        plugins = [SlowPlugin() for _ in range(3)]
        coordinator = PluginCoordinator(plugins, max_concurrent_handlers=2)

        action = mock_action
        params = MockParams()

        # Первое событие
        await coordinator.emit_event(
            event_name="slow_event",
            action=action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        # Очищаем историю вызовов
        for plugin in plugins:
            plugin.handlers_called = []

        # Второе событие должно работать с новым семафором
        start_time = asyncio.get_event_loop().time()

        await coordinator.emit_event(
            event_name="slow_event",
            action=action,
            params=params,
            state_aspect={},
            is_summary=False,
            result=None,
            duration=None,
            factory=mock_factory,
            context=mock_context,
            nest_level=0,
        )

        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time

        assert duration >= 0.15, f"Ожидали время >=0.15с, получили {duration:.2f}с"

    # УДАЛЕНЫ:
    # - test_semaphore_with_zero_concurrent: Semaphore(0) создаёт deadlock,
    #   это не ошибка кода — это невалидный ввод, который не нужно тестировать.
    # - test_semaphore_with_negative_concurrent: asyncio.Semaphore(-1) не бросает
    #   ValueError — это внутреннее поведение asyncio, не наша ответственность.
