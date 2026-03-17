"""
Тесты управления состояниями плагинов в PluginCoordinator.

Проверяем:
- Инициализацию состояний плагинов
- Идемпотентность инициализации (повторные вызовы не сбрасывают состояние)
- Кастомные начальные состояния
"""

import pytest

from action_machine.Plugins.PluginCoordinator import PluginCoordinator

from .conftest import CustomStatePlugin, SimplePlugin


class TestPluginCoordinatorStates:
    """Тесты управления состояниями плагинов."""

    # ------------------------------------------------------------------
    # ТЕСТЫ: Инициализация состояний
    # ------------------------------------------------------------------

    @pytest.mark.anyio
    async def test_init_plugin_states(self):
        """
        Инициализация состояний плагинов.

        Проверяем:
        - Состояния созданы для всех плагинов
        - Состояния имеют правильные начальные значения
        """
        plugin1 = SimplePlugin()
        plugin2 = SimplePlugin()
        coordinator = PluginCoordinator([plugin1, plugin2])

        await coordinator._init_plugin_states()

        assert len(coordinator._plugin_states) == 2
        assert id(plugin1) in coordinator._plugin_states
        assert id(plugin2) in coordinator._plugin_states
        assert coordinator._plugin_states[id(plugin1)] == {"counter": 0}
        assert coordinator._plugin_states[id(plugin2)] == {"counter": 0}

    @pytest.mark.anyio
    async def test_init_plugin_states_idempotent(self):
        """
        Повторная инициализация не меняет существующие состояния.

        Если состояние уже было изменено, оно не должно сбрасываться.
        """
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        # Первая инициализация
        await coordinator._init_plugin_states()
        state1 = coordinator._plugin_states[id(plugin)]

        # Изменяем состояние
        state1["counter"] = 42

        # Повторная инициализация
        await coordinator._init_plugin_states()

        # Состояние не должно сброситься
        assert coordinator._plugin_states[id(plugin)]["counter"] == 42

    @pytest.mark.anyio
    async def test_init_plugin_states_with_custom_initial(self):
        """
        Плагин с кастомным начальным состоянием.

        Проверяем, что get_initial_state() вызывается и возвращает
        правильное начальное состояние.
        """
        plugin = CustomStatePlugin()
        coordinator = PluginCoordinator([plugin])

        await coordinator._init_plugin_states()

        state = coordinator._plugin_states[id(plugin)]
        assert state == {"value": 100, "items": [1, 2, 3]}

    @pytest.mark.anyio
    async def test_init_plugin_states_preserves_independence(self):
        """
        Состояния разных плагинов независимы.

        Изменение состояния одного плагина не влияет на другие.
        """
        plugin1 = SimplePlugin()
        plugin2 = SimplePlugin()
        coordinator = PluginCoordinator([plugin1, plugin2])

        await coordinator._init_plugin_states()

        # Изменяем состояние первого плагина
        coordinator._plugin_states[id(plugin1)]["counter"] = 100

        # Второй плагин должен остаться неизменным
        assert coordinator._plugin_states[id(plugin2)]["counter"] == 0

    @pytest.mark.anyio
    async def test_init_plugin_states_lazy_initialization(self):
        """
        Состояния инициализируются лениво (только при первом обращении).

        До вызова _init_plugin_states словарь состояний пуст.
        """
        plugin = SimplePlugin()
        coordinator = PluginCoordinator([plugin])

        # До инициализации состояния пусты
        assert coordinator._plugin_states == {}

        # После инициализации состояние появляется
        await coordinator._init_plugin_states()
        assert len(coordinator._plugin_states) == 1

    @pytest.mark.anyio
    async def test_init_plugin_states_without_plugins(self):
        """
        Инициализация без плагинов не вызывает ошибок.
        """
        coordinator = PluginCoordinator([])

        # Не должно быть исключения
        await coordinator._init_plugin_states()

        assert coordinator._plugin_states == {}
