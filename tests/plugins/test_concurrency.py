# tests/plugins/test_concurrency.py
"""
Тесты параллельного и последовательного выполнения обработчиков плагинов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет стратегию выполнения обработчиков в PluginRunContext.
Стратегия выбирается автоматически на основе флагов ignore_exceptions
всех обработчиков, подписанных на текущее событие:

- ВСЕ обработчики имеют ignore_exceptions=True:
  Запуск параллельно через asyncio.gather(return_exceptions=True).
  Общее время ≈ время самого медленного обработчика. Падающие
  обработчики не прерывают остальных — их исключения подавляются.

- ХОТЯ БЫ ОДИН обработчик имеет ignore_exceptions=False:
  Запуск последовательно. Общее время ≈ сумма всех задержек.
  При ошибке критического обработчика (ignore_exceptions=False)
  исключение пробрасывается наружу и прерывает выполнение.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Параллельное выполнение (все ignore=True):
- Два медленных плагина по 50мс каждый завершаются за ~50мс (не ~100мс).
- Быстрый плагин завершается вместе с медленными.
- Все обработчики обновляют свои состояния.
- Падающий плагин (ignore=True) не прерывает остальных.

Последовательное выполнение (хотя бы один ignore=False):
- Два медленных плагина по 50мс выполняются за ~100мс (сумма).
- Смешанные флаги (ignore=True + ignore=False): все обработчики
  выполняются последовательно и обновляют состояния.

═══════════════════════════════════════════════════════════════════════════════
ЗАМЕЧАНИЕ О ТАЙМИНГАХ
═══════════════════════════════════════════════════════════════════════════════

Тесты с замером времени используют asyncio.get_event_loop().time() и
пороговые значения с запасом (0.09с для параллельного, 0.09с порог
для последовательного). На медленных CI-серверах возможны флакающие
результаты — при необходимости пороги можно увеличить.
"""

import asyncio

import pytest

from action_machine.intents.plugins.plugin_coordinator import PluginCoordinator

from .conftest import (
    FailingPluginIgnore,
    FastPluginIgnore,
    SlowPluginIgnore,
    SlowPluginNoIgnore,
    emit_global_finish,
)

# ═════════════════════════════════════════════════════════════════════════════
# Тесты параллельного выполнения (все ignore_exceptions=True)
# ═════════════════════════════════════════════════════════════════════════════


class TestParallelExecution:
    """
    Тесты параллельного выполнения обработчиков.

    Все обработчики имеют ignore_exceptions=True → PluginRunContext
    запускает их через asyncio.gather(return_exceptions=True).
    """

    @pytest.mark.anyio
    async def test_two_slow_plugins_run_in_parallel(self):
        """
        Два SlowPluginIgnore по 50мс каждый. При параллельном выполнении
        общее время ~50мс (время самого медленного), а не ~100мс (сумма).
        Порог 90мс с запасом на overhead event loop.
        """
        # Arrange — два медленных плагина + один быстрый
        slow1 = SlowPluginIgnore(delay=0.05)
        slow2 = SlowPluginIgnore(delay=0.05)
        fast = FastPluginIgnore()

        coordinator = PluginCoordinator(plugins=[slow1, slow2, fast])
        plugin_ctx = await coordinator.create_run_context()

        # Act — замеряем время выполнения
        start = asyncio.get_event_loop().time()
        await emit_global_finish(plugin_ctx)
        elapsed = asyncio.get_event_loop().time() - start

        # Assert — параллельно: ~50мс, не ~100мс
        assert elapsed < 0.09, (
            f"Параллельное выполнение заняло {elapsed:.3f}с, "
            f"ожидалось < 0.09с (два плагина по 0.05с параллельно)"
        )

        # Assert — все обработчики выполнились и обновили состояния
        assert plugin_ctx.get_plugin_state(slow1)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(slow2)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(fast)["calls"] == ["fast"]

    @pytest.mark.anyio
    async def test_failing_plugin_does_not_interrupt_others(self):
        """
        FailingPluginIgnore выбрасывает RuntimeError с ignore_exceptions=True.
        Ошибка подавляется, остальные плагины (SlowPluginIgnore, FastPluginIgnore)
        завершаются успешно и обновляют свои состояния.
        """
        # Arrange — медленный, быстрый и падающий плагины (все ignore=True)
        slow = SlowPluginIgnore(delay=0.05)
        fast = FastPluginIgnore()
        failing = FailingPluginIgnore()

        coordinator = PluginCoordinator(plugins=[slow, fast, failing])
        plugin_ctx = await coordinator.create_run_context()

        # Act — emit_event не должен выбросить исключение
        await emit_global_finish(plugin_ctx)

        # Assert — успешные плагины обновили состояния
        assert plugin_ctx.get_plugin_state(slow)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(fast)["calls"] == ["fast"]


# ═════════════════════════════════════════════════════════════════════════════
# Тесты последовательного выполнения (хотя бы один ignore_exceptions=False)
# ═════════════════════════════════════════════════════════════════════════════


class TestSequentialExecution:
    """
    Тесты последовательного выполнения обработчиков.

    Хотя бы один обработчик имеет ignore_exceptions=False →
    PluginRunContext запускает все обработчики последовательно.
    """

    @pytest.mark.anyio
    async def test_two_slow_plugins_run_sequentially(self):
        """
        Два SlowPluginNoIgnore по 50мс каждый. При последовательном
        выполнении общее время ~100мс (сумма), а не ~50мс (параллельно).
        Порог: elapsed >= 0.09с (с учётом overhead).
        """
        # Arrange — два медленных плагина с ignore=False
        slow1 = SlowPluginNoIgnore(delay=0.05)
        slow2 = SlowPluginNoIgnore(delay=0.05)

        coordinator = PluginCoordinator(plugins=[slow1, slow2])
        plugin_ctx = await coordinator.create_run_context()

        # Act — замеряем время выполнения
        start = asyncio.get_event_loop().time()
        await emit_global_finish(plugin_ctx)
        elapsed = asyncio.get_event_loop().time() - start

        # Assert — последовательно: ~100мс, порог >= 90мс
        assert elapsed >= 0.09, (
            f"Последовательное выполнение заняло {elapsed:.3f}с, "
            f"ожидалось >= 0.09с (два плагина по 0.05с последовательно)"
        )

        # Assert — оба обработчика выполнились
        assert plugin_ctx.get_plugin_state(slow1)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(slow2)["calls"] == ["slow"]

    @pytest.mark.anyio
    async def test_mixed_flags_all_handlers_complete(self):
        """
        SlowPluginNoIgnore (ignore=False) + FastPluginIgnore (ignore=True).
        Наличие одного ignore=False переключает на последовательное
        выполнение. Оба обработчика завершаются и обновляют состояния.
        """
        # Arrange — критический медленный + некритический быстрый
        critical = SlowPluginNoIgnore(delay=0.01)
        metrics = FastPluginIgnore()

        coordinator = PluginCoordinator(plugins=[critical, metrics])
        plugin_ctx = await coordinator.create_run_context()

        # Act — последовательное выполнение из-за ignore=False
        await emit_global_finish(plugin_ctx)

        # Assert — оба обработчика выполнились
        assert plugin_ctx.get_plugin_state(critical)["calls"] == ["slow"]
        assert plugin_ctx.get_plugin_state(metrics)["calls"] == ["fast"]
