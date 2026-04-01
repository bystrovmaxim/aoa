# tests2/plugins/test_handlers.py
"""
Тесты выполнения обработчиков плагинов и управления per-request состояниями.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет ключевой механизм плагинной системы: обработчик получает
текущее per-request состояние плагина, обновляет его и возвращает.
PluginRunContext сохраняет обновлённое состояние и передаёт его
в следующий обработчик того же плагина.

Состояния создаются через PluginCoordinator.create_run_context(),
который вызывает get_initial_state() для каждого плагина. Каждый
вызов create_run_context() создаёт новый изолированный контекст —
состояния одного run() не влияют на другой.

═══════════════════════════════════════════════════════════════════════════════
ПОКРЫВАЕМЫЕ СЦЕНАРИИ
═══════════════════════════════════════════════════════════════════════════════

Выполнение обработчиков:
- Один обработчик одного плагина обновляет state["count"].
- Два обработчика одного плагина на одно событие: оба выполняются,
  обновляют разные поля общего состояния.
- Два плагина — независимые состояния: изменения одного не видны другому.

Инициализация состояний:
- create_run_context() инициализирует состояния из get_initial_state().
- Кастомное начальное состояние через параметр конструктора плагина.
- Повторный create_run_context() создаёт свежие состояния, независимые
  от предыдущего контекста (идемпотентность).
"""

import pytest

from action_machine.plugins.plugin_coordinator import PluginCoordinator

from .conftest import (
    CounterPlugin,
    CustomInitPlugin,
    DualHandlerPlugin,
    emit_global_finish,
)

# ═════════════════════════════════════════════════════════════════════════════
# Тесты выполнения обработчиков
# ═════════════════════════════════════════════════════════════════════════════


class TestRunHandlers:
    """Тесты выполнения обработчиков и обновления per-request состояний."""

    @pytest.mark.anyio
    async def test_single_handler_updates_state(self):
        """
        Один обработчик CounterPlugin инкрементирует state["count"]
        при каждом событии global_finish.
        """
        # Arrange — один плагин-счётчик, контекст с начальным состоянием
        plugin = CounterPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — отправляем одно событие global_finish
        await emit_global_finish(plugin_ctx)

        # Assert — счётчик инкрементировался
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["count"] == 1

    @pytest.mark.anyio
    async def test_multiple_events_accumulate(self):
        """
        Три последовательных события global_finish — счётчик
        инкрементируется трижды в рамках одного контекста.
        """
        # Arrange — плагин-счётчик
        plugin = CounterPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — три события подряд
        await emit_global_finish(plugin_ctx)
        await emit_global_finish(plugin_ctx)
        await emit_global_finish(plugin_ctx)

        # Assert — три инкремента
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["count"] == 3

    @pytest.mark.anyio
    async def test_two_handlers_same_plugin(self):
        """
        DualHandlerPlugin имеет два обработчика на global_finish.
        Оба выполняются и обновляют разные поля общего состояния:
        handler_a → state["a"] += 1, handler_b → state["b"] += 10.
        """
        # Arrange — плагин с двумя обработчиками
        plugin = DualHandlerPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])
        plugin_ctx = await coordinator.create_run_context()

        # Act — одно событие запускает оба обработчика
        await emit_global_finish(plugin_ctx)

        # Assert — оба поля обновлены
        state = plugin_ctx.get_plugin_state(plugin)
        assert state["a"] == 1
        assert state["b"] == 10

    @pytest.mark.anyio
    async def test_two_plugins_independent_states(self):
        """
        CounterPlugin и DualHandlerPlugin имеют независимые состояния.
        Изменения одного плагина не видны другому.
        """
        # Arrange — два плагина с разными состояниями
        counter = CounterPlugin()
        dual = DualHandlerPlugin()
        coordinator = PluginCoordinator(plugins=[counter, dual])
        plugin_ctx = await coordinator.create_run_context()

        # Act — одно событие обрабатывается обоими плагинами
        await emit_global_finish(plugin_ctx)

        # Assert — состояния независимы
        counter_state = plugin_ctx.get_plugin_state(counter)
        dual_state = plugin_ctx.get_plugin_state(dual)

        assert counter_state["count"] == 1
        assert "a" not in counter_state
        assert "b" not in counter_state

        assert dual_state["a"] == 1
        assert dual_state["b"] == 10
        assert "count" not in dual_state


# ═════════════════════════════════════════════════════════════════════════════
# Тесты инициализации состояний
# ═════════════════════════════════════════════════════════════════════════════


class TestPluginStates:
    """Тесты инициализации и изоляции per-request состояний плагинов."""

    @pytest.mark.anyio
    async def test_initial_state_from_get_initial_state(self):
        """
        create_run_context() инициализирует состояние плагина
        значением из get_initial_state(). CounterPlugin возвращает
        {"count": 0}.
        """
        # Arrange — плагин-счётчик
        plugin = CounterPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])

        # Act — создаём контекст (вызывает get_initial_state)
        plugin_ctx = await coordinator.create_run_context()

        # Assert — начальное состояние соответствует get_initial_state()
        state = plugin_ctx.get_plugin_state(plugin)
        assert state == {"count": 0}

    @pytest.mark.anyio
    async def test_custom_initial_value_through_constructor(self):
        """
        CustomInitPlugin принимает initial_value в конструкторе.
        get_initial_state() возвращает {"value": initial_value}.
        """
        # Arrange — плагин с кастомным начальным значением 42
        plugin = CustomInitPlugin(initial_value=42)
        coordinator = PluginCoordinator(plugins=[plugin])

        # Act — создаём контекст
        plugin_ctx = await coordinator.create_run_context()

        # Assert — начальное состояние содержит кастомное значение
        state = plugin_ctx.get_plugin_state(plugin)
        assert state == {"value": 42}

    @pytest.mark.anyio
    async def test_new_context_has_fresh_states(self):
        """
        Повторный вызов create_run_context() создаёт новый контекст
        с начальными состояниями. Предыдущий контекст не затрагивается.
        Это гарантирует изоляцию между вызовами machine.run().
        """
        # Arrange — плагин-счётчик, координатор
        plugin = CounterPlugin()
        coordinator = PluginCoordinator(plugins=[plugin])

        # Act — первый контекст: инкрементируем счётчик
        ctx1 = await coordinator.create_run_context()
        await emit_global_finish(ctx1)
        state1_after = ctx1.get_plugin_state(plugin)

        # Act — второй контекст: свежее начальное состояние
        ctx2 = await coordinator.create_run_context()
        state2_initial = ctx2.get_plugin_state(plugin)

        # Assert — первый контекст: счётчик == 1
        assert state1_after["count"] == 1

        # Assert — второй контекст: счётчик == 0 (свежее состояние)
        assert state2_initial["count"] == 0

        # Assert — первый контекст не изменился после создания второго
        assert ctx1.get_plugin_state(plugin)["count"] == 1
