# src/action_machine/plugins/plugin_coordinator.py
"""
PluginCoordinator — stateless-координатор плагинов для ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

PluginCoordinator отвечает за хранение списка плагинов и создание
изолированных контекстов выполнения (PluginRunContext) для каждого
вызова run(). Координатор полностью stateless — он не хранит
никакого мутабельного состояния между запросами.

Вся мутабельная информация (состояния плагинов, накопленные данные
обработчиков) инкапсулирована в PluginRunContext, который живёт ровно
столько, сколько длится один вызов run().

═══════════════════════════════════════════════════════════════════════════════
РОЛЬ В АРХИТЕКТУРЕ
═══════════════════════════════════════════════════════════════════════════════

PluginCoordinator — единственная точка создания PluginRunContext.
ActionProductMachine хранит экземпляр координатора и вызывает
create_run_context() в начале каждого _run_internal(). Возвращённый
контекст используется для всех emit_event() внутри этого run()
и уничтожается по завершении.

    ActionProductMachine
        │
        │  self._plugin_coordinator = PluginCoordinator(plugins=[...])
        │
        │  В каждом _run_internal():
        │    plugin_ctx = await self._plugin_coordinator.create_run_context()
        │    ...
        │    await plugin_ctx.emit_event(GlobalStartEvent(...), ...)
        │    ... конвейер аспектов ...
        │    await plugin_ctx.emit_event(GlobalFinishEvent(...), ...)
        │    ... plugin_ctx уничтожается (выходит из scope) ...
        ▼

═══════════════════════════════════════════════════════════════════════════════
ИЗОЛЯЦИЯ МЕЖДУ ЗАПРОСАМИ
═══════════════════════════════════════════════════════════════════════════════

Каждый run() получает свой PluginRunContext. Параллельные вызовы run()
(через asyncio.gather) работают с разными контекстами и не влияют
друг на друга. Состояние плагина из одного run() не протекает в другой.

Если плагину необходимо накапливать данные между запросами (метрики,
счётчики), он использует внешнее хранилище, переданное через
конструктор плагина. Фреймворк обеспечивает изоляцию per-request
состояния; политика аккумуляции — ответственность пользователя.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.plugins.plugin_coordinator import PluginCoordinator

    coordinator = PluginCoordinator(plugins=[CounterPlugin(), MetricsPlugin()])

    # В начале каждого run():
    plugin_ctx = await coordinator.create_run_context()

    # Отправка типизированных событий через контекст:
    await plugin_ctx.emit_event(
        GlobalStartEvent(action_class=..., ...),
        log_coordinator=log_coord,
        machine_name="ActionProductMachine",
        mode="production",
        coordinator=gate_coordinator,
    )

    # Доступ к состоянию для тестов:
    state = plugin_ctx.get_plugin_state(counter_plugin)
"""

from __future__ import annotations

from typing import Any

from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_run_context import PluginRunContext


class PluginCoordinator:
    """
    Stateless-координатор жизненного цикла плагинов.

    Хранит только список экземпляров плагинов. Не содержит мутабельного
    состояния между запросами. Для каждого вызова run() создаёт
    изолированный PluginRunContext через create_run_context().

    Атрибуты:
        _plugins : list[Plugin]
            Список экземпляров плагинов, переданных при создании.
            Не изменяется после инициализации.
    """

    def __init__(
        self,
        plugins: list[Plugin],
    ) -> None:
        """
        Инициализирует координатор плагинов.

        Аргументы:
            plugins: список экземпляров плагинов. Каждый плагин должен
                     наследовать Plugin и реализовывать get_initial_state().
                     Методы-обработчики помечаются декоратором @on
                     с классом события как первым аргументом.
        """
        self._plugins: list[Plugin] = plugins

    async def create_run_context(self) -> PluginRunContext:
        """
        Создаёт изолированный контекст плагинов для одного вызова run().

        Для каждого плагина асинхронно вызывает get_initial_state()
        и сохраняет результат в словаре начальных состояний. Затем
        создаёт PluginRunContext с этим словарём.

        Вызывается в начале ActionProductMachine._run_internal().
        Возвращённый контекст используется для всех emit_event()
        внутри этого run() и уничтожается по завершении.

        Возвращает:
            PluginRunContext — изолированный контекст с начальными
            состояниями всех плагинов.
        """
        initial_states: dict[int, Any] = {}
        for plugin in self._plugins:
            plugin_id = id(plugin)
            state = await plugin.get_initial_state()
            initial_states[plugin_id] = state

        return PluginRunContext(
            plugins=self._plugins,
            initial_states=initial_states,
        )

    @property
    def plugins(self) -> list[Plugin]:
        """
        Возвращает список зарегистрированных плагинов.

        Используется для инспекции и тестирования.
        """
        return self._plugins
