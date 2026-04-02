# tests/plugins/conftest.py
"""
Фикстуры и тестовые плагины для тестирования плагинной системы ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит тестовые плагины — классы, наследующие Plugin с обработчиками
через @on — и pytest-фикстуры, специфичные для пакета tests/plugins/.

Тестовые плагины определяются здесь, а не в tests/domain/, потому что
они не являются частью бизнес-доменной модели. Это инфраструктурные
компоненты тестов, специфичные для проверки плагинной подсистемы.

Общие фикстуры (coordinator, bench, mock_payment и т.д.) наследуются
из tests/conftest.py. Этот файл дополняет их фикстурами для плагинов.

═══════════════════════════════════════════════════════════════════════════════
ТЕСТОВЫЕ ПЛАГИНЫ
═══════════════════════════════════════════════════════════════════════════════

CounterPlugin
    Минимальный плагин-счётчик. Один обработчик global_finish для ".*".
    Инкрементирует state["count"] при каждом вызове. ignore_exceptions=False.
    Используется в тестах handlers и states.

DualHandlerPlugin
    Плагин с двумя обработчиками на одно событие (global_finish).
    Обработчик handler_a инкрементирует state["a"], handler_b добавляет 10
    к state["b"]. ignore_exceptions=False. Используется для проверки
    множественных обработчиков одного плагина.

CustomInitPlugin
    Плагин с параметризованным начальным состоянием. Принимает initial_value
    в конструкторе, возвращает {"value": initial_value} из get_initial_state().
    Обработчик increment инкрементирует value. Используется для проверки
    кастомной инициализации.

RecordingPlugin
    Плагин, записывающий все полученные события в state["events"] как список
    словарей с event_name, action_name, nest_level. Используется для проверки
    корректности PluginEvent.

SelectivePlugin
    Плагин с фильтром action_filter=".*DummyAction$". Реагирует только на
    события от DummyAction. Используется для проверки фильтрации по имени
    действия.

SlowPluginIgnore
    Плагин с задержкой asyncio.sleep(delay). ignore_exceptions=True.
    Используется для проверки параллельного выполнения: два таких плагина
    по 50мс каждый должны завершиться за ~50мс (параллельно), а не за ~100мс.

FastPluginIgnore
    Плагин без задержки. ignore_exceptions=True. Используется в паре
    со SlowPluginIgnore для проверки параллельности.

SlowPluginNoIgnore
    Плагин с задержкой. ignore_exceptions=False. При наличии хотя бы
    одного такого обработчика PluginRunContext переключается на
    последовательное выполнение.

FastPluginNoIgnore
    Плагин без задержки. ignore_exceptions=False. Используется в паре
    со SlowPluginNoIgnore для проверки последовательности.

FailingPluginIgnore
    Плагин с обработчиком, выбрасывающим RuntimeError. ignore_exceptions=True.
    Ошибка подавляется, остальные плагины продолжают работу.

IgnoredErrorPlugin
    Плагин, мутирующий state до raise. state["before_error"]=True записывается
    до исключения. state["after_error"] остаётся False (код после raise
    не выполняется). Демонстрирует in-place мутацию dict при ошибке.

PropagatedErrorPlugin
    Плагин с ignore_exceptions=False, выбрасывающий RuntimeError.
    Ошибка пробрасывается наружу через emit_event.

CustomExceptionPlugin
    Плагин с ignore_exceptions=False, выбрасывающий кастомное исключение
    CustomPluginError. Проверяет, что тип исключения сохраняется.

SuccessAfterFailPlugin
    Плагин с успешным обработчиком. Используется для проверки, что
    исключение критического плагина прерывает выполнение.

AlphaPlugin
    Плагин с обработчиком global_finish для ".*" — реагирует на все действия.

BetaPlugin
    Плагин с обработчиком global_finish для ".*Order.*" — реагирует только
    на действия, содержащие "Order" в имени.

GammaPlugin
    Плагин с обработчиком global_start (не global_finish).

MultiEventPlugin
    Плагин с тремя обработчиками: global_start для ".*", global_finish
    для ".*", global_finish для ".*Order.*". Используется для проверки
    множественных подписок одного плагина.

═══════════════════════════════════════════════════════════════════════════════
ФИКСТУРЫ
═══════════════════════════════════════════════════════════════════════════════

empty_factory
    Пустая DependencyFactory без зависимостей. Требуется для PluginEvent.deps.

═══════════════════════════════════════════════════════════════════════════════
ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
═══════════════════════════════════════════════════════════════════════════════

emit_global_finish(plugin_ctx, action, nest_level)
    Отправляет событие global_finish через PluginRunContext. Используется
    как сокращение в тестах, избавляя от повторения 10 параметров emit_event.
"""

import asyncio

import pytest

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.dependencies.dependency_factory import DependencyFactory
from action_machine.plugins.decorators import on
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_event import PluginEvent
from action_machine.plugins.plugin_run_context import PluginRunContext
from tests.domain import PingAction

# ═════════════════════════════════════════════════════════════════════════════
# Кастомное исключение для тестов
# ═════════════════════════════════════════════════════════════════════════════


class CustomPluginError(Exception):
    """Кастомное исключение для проверки типа пробрасываемой ошибки."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые плагины: базовые (handlers, states)
# ═════════════════════════════════════════════════════════════════════════════


class CounterPlugin(Plugin):
    """
    Минимальный плагин-счётчик.

    Один обработчик global_finish для всех действий. Инкрементирует
    state["count"] при каждом вызове. ignore_exceptions=False —
    критический обработчик, ошибка пробрасывается.
    """

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def count(self, state: dict, event: PluginEvent, log) -> dict:
        state["count"] += 1
        return state


class DualHandlerPlugin(Plugin):
    """
    Плагин с двумя обработчиками на одно событие (global_finish).

    handler_a инкрементирует state["a"] на 1.
    handler_b инкрементирует state["b"] на 10.
    Оба ignore_exceptions=False — последовательное выполнение.
    """

    async def get_initial_state(self) -> dict:
        return {"a": 0, "b": 0}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def handler_a(self, state: dict, event: PluginEvent, log) -> dict:
        state["a"] += 1
        return state

    @on("global_finish", ".*", ignore_exceptions=False)
    async def handler_b(self, state: dict, event: PluginEvent, log) -> dict:
        state["b"] += 10
        return state


class CustomInitPlugin(Plugin):
    """
    Плагин с параметризованным начальным состоянием.

    Принимает initial_value в конструкторе. get_initial_state() возвращает
    {"value": initial_value}. Обработчик increment добавляет 1 к value.
    """

    def __init__(self, initial_value: int = 100):
        self._initial = initial_value

    async def get_initial_state(self) -> dict:
        return {"value": self._initial}

    @on("global_finish", ".*")
    async def increment(self, state: dict, event: PluginEvent, log) -> dict:
        state["value"] += 1
        return state


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые плагины: emit (запись событий, фильтрация)
# ═════════════════════════════════════════════════════════════════════════════


class RecordingPlugin(Plugin):
    """
    Плагин, записывающий все полученные события global_finish.

    Каждое событие добавляется как словарь с event_name, action_name,
    nest_level в state["events"]. Используется для проверки корректности
    полей PluginEvent и подсчёта вызовов.
    """

    async def get_initial_state(self) -> dict:
        return {"events": []}

    @on("global_finish", ".*")
    async def record_finish(self, state: dict, event: PluginEvent, log) -> dict:
        state["events"].append({
            "event_name": event.event_name,
            "action_name": event.action_name,
            "nest_level": event.nest_level,
        })
        return state


class SelectivePlugin(Plugin):
    """
    Плагин с фильтром по имени действия.

    action_filter=".*PingAction$" — реагирует только на PingAction.
    Используется для проверки, что события от других действий
    не доставляются этому плагину.
    """

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on("global_finish", ".*PingAction$")
    async def on_ping(self, state: dict, event: PluginEvent, log) -> dict:
        state["count"] += 1
        return state


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые плагины: concurrency (параллельность/последовательность)
# ═════════════════════════════════════════════════════════════════════════════


class SlowPluginIgnore(Plugin):
    """
    Плагин с задержкой asyncio.sleep(delay). ignore_exceptions=True.

    При параллельном выполнении два таких плагина по 50мс каждый
    завершаются за ~50мс (время самого медленного), а не за ~100мс.
    """

    def __init__(self, delay: float = 0.05):
        self._delay = delay

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on("global_finish", ".*", ignore_exceptions=True)
    async def slow_handler(self, state: dict, event: PluginEvent, log) -> dict:
        await asyncio.sleep(self._delay)
        state["calls"].append("slow")
        return state


class FastPluginIgnore(Plugin):
    """
    Быстрый плагин без задержки. ignore_exceptions=True.

    Используется в паре со SlowPluginIgnore для проверки, что все
    обработчики завершаются при параллельном выполнении.
    """

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on("global_finish", ".*", ignore_exceptions=True)
    async def fast_handler(self, state: dict, event: PluginEvent, log) -> dict:
        state["calls"].append("fast")
        return state


class SlowPluginNoIgnore(Plugin):
    """
    Плагин с задержкой. ignore_exceptions=False.

    Наличие хотя бы одного обработчика с ignore_exceptions=False
    переключает PluginRunContext на последовательное выполнение.
    Два таких плагина по 50мс завершаются за ~100мс (сумма).
    """

    def __init__(self, delay: float = 0.05):
        self._delay = delay

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def slow_handler(self, state: dict, event: PluginEvent, log) -> dict:
        await asyncio.sleep(self._delay)
        state["calls"].append("slow")
        return state


class FastPluginNoIgnore(Plugin):
    """Быстрый плагин. ignore_exceptions=False."""

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def fast_handler(self, state: dict, event: PluginEvent, log) -> dict:
        state["calls"].append("fast")
        return state


class FailingPluginIgnore(Plugin):
    """
    Плагин с обработчиком, выбрасывающим RuntimeError. ignore_exceptions=True.

    Ошибка подавляется. Используется для проверки, что падающий плагин
    не прерывает параллельное выполнение остальных.
    """

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_finish", ".*", ignore_exceptions=True)
    async def failing_handler(self, state: dict, event: PluginEvent, log) -> dict:
        raise RuntimeError("Plugin error")


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые плагины: exceptions (обработка ошибок)
# ═════════════════════════════════════════════════════════════════════════════


class IgnoredErrorPlugin(Plugin):
    """
    Плагин, мутирующий state до raise. ignore_exceptions=True.

    state["before_error"]=True записывается до исключения (in-place мутация
    dict). state["after_error"] остаётся False — код после raise не выполняется.
    Демонстрирует, что in-place мутации dict видны даже при подавленной ошибке.
    """

    async def get_initial_state(self) -> dict:
        return {"before_error": False, "after_error": False}

    @on("global_finish", ".*", ignore_exceptions=True)
    async def failing_handler(self, state: dict, event: PluginEvent, log) -> dict:
        state["before_error"] = True
        raise RuntimeError("Ignored error")
        # state["after_error"] = True  # не выполнится


class PropagatedErrorPlugin(Plugin):
    """
    Плагин с ignore_exceptions=False, выбрасывающий RuntimeError.

    Ошибка пробрасывается наружу через emit_event(). Используется для
    проверки, что критические ошибки прерывают выполнение.
    """

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def strict_handler(self, state: dict, event: PluginEvent, log) -> dict:
        raise RuntimeError("Strict error must propagate")


class CustomExceptionPlugin(Plugin):
    """
    Плагин с ignore_exceptions=False, выбрасывающий CustomPluginError.

    Проверяет, что тип кастомного исключения сохраняется при пробросе.
    """

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def custom_handler(self, state: dict, event: PluginEvent, log) -> dict:
        raise CustomPluginError("Custom plugin error")


class SuccessAfterFailPlugin(Plugin):
    """
    Плагин с успешным обработчиком. ignore_exceptions=False.

    Используется для проверки, что при совместной работе с PropagatedErrorPlugin
    последовательное выполнение прерывается на критической ошибке.
    """

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on("global_finish", ".*", ignore_exceptions=False)
    async def success_handler(self, state: dict, event: PluginEvent, log) -> dict:
        state["count"] += 1
        return state


# ═════════════════════════════════════════════════════════════════════════════
# Тестовые плагины: find_plugin (поиск обработчиков, фильтрация)
# ═════════════════════════════════════════════════════════════════════════════


class AlphaPlugin(Plugin):
    """
    Плагин с обработчиком global_finish для ".*" — реагирует на все действия.
    """

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_finish", ".*")
    async def on_finish(self, state: dict, event: PluginEvent, log) -> dict:
        return state


class BetaPlugin(Plugin):
    """
    Плагин с обработчиком global_finish для ".*Order.*".

    Реагирует только на действия, содержащие "Order" в полном имени класса.
    """

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_finish", ".*Order.*")
    async def on_order_finish(self, state: dict, event: PluginEvent, log) -> dict:
        return state


class GammaPlugin(Plugin):
    """
    Плагин с обработчиком global_start (не global_finish).

    Используется для проверки, что поиск по global_finish не возвращает
    обработчики, подписанные на global_start.
    """

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_start", ".*")
    async def on_start(self, state: dict, event: PluginEvent, log) -> dict:
        return state


class MultiEventPlugin(Plugin):
    """
    Плагин с тремя обработчиками на разные события и фильтры.

    on_start: global_start для ".*".
    on_finish: global_finish для ".*".
    on_order_finish: global_finish для ".*Order.*".

    Для global_finish + "*OrderAction" должны найтись два обработчика.
    Для global_finish + "PingAction" — один (on_finish).
    Для global_start + любое действие — один (on_start).
    """

    async def get_initial_state(self) -> dict:
        return {}

    @on("global_start", ".*")
    async def on_start(self, state: dict, event: PluginEvent, log) -> dict:
        return state

    @on("global_finish", ".*")
    async def on_finish(self, state: dict, event: PluginEvent, log) -> dict:
        return state

    @on("global_finish", ".*Order.*")
    async def on_order_finish(self, state: dict, event: PluginEvent, log) -> dict:
        return state


# ═════════════════════════════════════════════════════════════════════════════
# Фикстуры
# ═════════════════════════════════════════════════════════════════════════════


@pytest.fixture()
def empty_factory() -> DependencyFactory:
    """
    Пустая DependencyFactory без зависимостей.

    Требуется для поля deps объекта PluginEvent. Плагинам в тестах
    зависимости не нужны, но PluginEvent ожидает DependencyFactory.
    """
    return DependencyFactory(())


# ═════════════════════════════════════════════════════════════════════════════
# Вспомогательные функции
# ═════════════════════════════════════════════════════════════════════════════


async def emit_global_finish(
    plugin_ctx: PluginRunContext,
    action: object | None = None,
    nest_level: int = 0,
) -> None:
    """
    Отправляет событие global_finish через PluginRunContext.

    Сокращение для тестов — избавляет от повторения 10 параметров
    emit_event() в каждом тесте. Использует PingAction из доменной
    модели как действие по умолчанию.

    Аргументы:
        plugin_ctx: контекст плагинов, созданный через create_run_context().
        action: экземпляр действия. По умолчанию PingAction().
        nest_level: уровень вложенности. По умолчанию 0.
    """
    if action is None:
        action = PingAction()
    await plugin_ctx.emit_event(
        event_name="global_finish",
        action=action,
        params=BaseParams(),
        state_aspect=None,
        is_summary=False,
        result=None,
        duration=1.0,
        factory=DependencyFactory(()),
        context=Context(),
        nest_level=nest_level,
    )
