# tests/plugins/conftest.py
"""
Тестовые плагины и фикстуры для пакета tests/plugins/.
═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════
Содержит тестовые плагины, хелперы эмиссии событий и фикстуры,
используемые всеми тестовыми модулями в tests/plugins/.

Все плагины используют типизированную подписку через классы событий
из иерархии BasePluginEvent [1]:
    @on(GlobalFinishEvent)            — вместо @on("global_finish", ".*")
    @on(GlobalStartEvent)             — вместо @on("global_start", ".*")
    @on(BeforeRegularAspectEvent)     — вместо @on("before:aspect_name", ".*")
    @on(AfterRegularAspectEvent)      — вместо @on("after:aspect_name", ".*")
    @on(UnhandledErrorEvent)          — вместо @on("on_error", ".*")

Обработчики получают конкретные типизированные объекты событий
вместо единого PluginEvent с Optional-полями.
═══════════════════════════════════════════════════════════════════════════════
ХЕЛПЕР emit_global_finish()
═══════════════════════════════════════════════════════════════════════════════
Создаёт объект GlobalFinishEvent с тестовыми значениями полей и передаёт
в plugin_ctx.emit_event(). Используется в test_emit.py, test_handlers.py,
test_exceptions.py, test_concurrency.py для эмуляции события завершения
действия без запуска полного конвейера машины.

Аналогичные хелперы emit_global_start(), emit_before_regular(),
emit_after_regular() создают другие типы событий для тестов фильтрации.
═══════════════════════════════════════════════════════════════════════════════
ТЕСТОВЫЕ ПЛАГИНЫ
═══════════════════════════════════════════════════════════════════════════════

CounterPlugin
    Минимальный плагин-счётчик. Один обработчик GlobalFinishEvent для
    всех действий. Инкрементирует state["count"]. ignore_exceptions=False.

DualHandlerPlugin
    Плагин с двумя обработчиками на одно событие (GlobalFinishEvent).
    on_handler_a инкрементирует state["a"] на 1.
    on_handler_b инкрементирует state["b"] на 10.
    Оба ignore_exceptions=False — последовательное выполнение.

CustomInitPlugin
    Плагин с параметризованным начальным состоянием.
    Принимает initial_value в конструкторе.

RecordingPlugin
    Плагин-записыватель. Записывает тип события и action_name
    в state["events"] при каждом GlobalFinishEvent.

SelectivePlugin
    Плагин с фильтром action_name_pattern. Реагирует только на действия,
    содержащие "Order" в имени.

AlphaPlugin
    Плагин с обработчиком GlobalFinishEvent — реагирует на все действия.

BetaPlugin
    Плагин с обработчиком GlobalFinishEvent с action_name_pattern=".*Order.*".
    Реагирует только на действия с "Order" в имени.

GammaPlugin
    Плагин с обработчиком GlobalStartEvent (не GlobalFinishEvent).
    Используется для проверки, что поиск по GlobalFinishEvent не возвращает
    обработчики, подписанные на GlobalStartEvent.

MultiEventPlugin
    Плагин с тремя обработчиками на разные события и фильтры.
    on_start: GlobalStartEvent.
    on_finish: GlobalFinishEvent.
    on_order_finish: GlobalFinishEvent с action_name_pattern=".*Order.*".

IgnoredErrorPlugin
    Плагин с ignore_exceptions=True, который мутирует state перед raise.
    Проверяет видимость in-place мутации при подавленной ошибке.

PropagatedErrorPlugin
    Плагин с ignore_exceptions=False, выбрасывающий RuntimeError.
    Ошибка пробрасывается наружу через emit_event().

CustomExceptionPlugin
    Плагин с ignore_exceptions=False, выбрасывающий CustomPluginError.
    Проверяет, что тип кастомного исключения сохраняется при пробросе.

SuccessAfterFailPlugin
    Плагин с успешным обработчиком. ignore_exceptions=False.
    Используется для проверки, что исключение критического плагина
    прерывает выполнение.

SlowParallelPlugin
    Плагин с задержкой 0.1с. ignore_exceptions=True.
    Используется для проверки параллельного выполнения.

SlowSequentialPlugin
    Плагин с задержкой 0.1с. ignore_exceptions=False.
    Используется для проверки последовательного выполнения.
"""
from __future__ import annotations

import asyncio

from action_machine.context.context import Context
from action_machine.context.user_info import UserInfo
from action_machine.core.base_params import BaseParams
from action_machine.core.base_result import BaseResult
from action_machine.plugins.decorators import on
from action_machine.plugins.events import (
    GlobalFinishEvent,
    GlobalStartEvent,
)
from action_machine.plugins.plugin import Plugin
from action_machine.plugins.plugin_run_context import PluginRunContext
from tests.domain_model import PingAction

# ═════════════════════════════════════════════════════════════════════════════
# Кастомное исключение для тестов
# ═════════════════════════════════════════════════════════════════════════════

class CustomPluginError(Exception):
    """Кастомное исключение для тестов пробрасывания ошибок плагинов."""
    pass


# ═════════════════════════════════════════════════════════════════════════════
# Тестовый контекст и параметры для хелперов
# ═════════════════════════════════════════════════════════════════════════════

_TEST_CONTEXT = Context(user=UserInfo(user_id="test_user", roles=["tester"]))
_TEST_PARAMS = BaseParams()
_TEST_ACTION_CLASS = PingAction
_TEST_ACTION_NAME = "tests.domain.ping_action.PingAction"


# ═════════════════════════════════════════════════════════════════════════════
# Хелперы эмиссии событий
# ═════════════════════════════════════════════════════════════════════════════

async def emit_global_finish(
    plugin_ctx: PluginRunContext,
    *,
    action_name: str = _TEST_ACTION_NAME,
    action_class: type = _TEST_ACTION_CLASS,
    context: Context | None = None,
    params: BaseParams | None = None,
    result: BaseResult | None = None,
    duration_ms: float = 0.0,
    nest_level: int = 1,
) -> None:
    """
    Создаёт GlobalFinishEvent с тестовыми значениями и эмитирует через plugin_ctx.

    Используется в test_emit.py, test_handlers.py, test_exceptions.py,
    test_concurrency.py для эмуляции события завершения действия без
    запуска полного конвейера машины.

    Аргументы:
        plugin_ctx: контекст плагинов для эмиссии.
        action_name: полное строковое имя действия.
        action_class: тип действия.
        context: контекст выполнения (по умолчанию тестовый).
        params: входные параметры (по умолчанию пустые).
        result: результат действия (по умолчанию пустой).
        duration_ms: длительность в миллисекундах.
        nest_level: уровень вложенности.
    """
    event = GlobalFinishEvent(
        action_class=action_class,
        action_name=action_name,
        nest_level=nest_level,
        context=context or _TEST_CONTEXT,
        params=params or _TEST_PARAMS,
        result=result or BaseResult(),
        duration_ms=duration_ms,
    )
    await plugin_ctx.emit_event(event)


async def emit_global_start(
    plugin_ctx: PluginRunContext,
    *,
    action_name: str = _TEST_ACTION_NAME,
    action_class: type = _TEST_ACTION_CLASS,
    context: Context | None = None,
    params: BaseParams | None = None,
    nest_level: int = 1,
) -> None:
    """
    Создаёт GlobalStartEvent с тестовыми значениями и эмитирует через plugin_ctx.

    Аргументы:
        plugin_ctx: контекст плагинов для эмиссии.
        action_name: полное строковое имя действия.
        action_class: тип действия.
        context: контекст выполнения (по умолчанию тестовый).
        params: входные параметры (по умолчанию пустые).
        nest_level: уровень вложенности.
    """
    event = GlobalStartEvent(
        action_class=action_class,
        action_name=action_name,
        nest_level=nest_level,
        context=context or _TEST_CONTEXT,
        params=params or _TEST_PARAMS,
    )
    await plugin_ctx.emit_event(event)


def make_global_finish_event(
    *,
    action_name: str = _TEST_ACTION_NAME,
    action_class: type = _TEST_ACTION_CLASS,
    context: Context | None = None,
    params: BaseParams | None = None,
    result: BaseResult | None = None,
    duration_ms: float = 0.0,
    nest_level: int = 1,
) -> GlobalFinishEvent:
    """
    Создаёт GlobalFinishEvent без эмиссии — для тестов get_handlers().

    Аргументы:
        action_name: полное строковое имя действия.
        action_class: тип действия.
        context: контекст выполнения.
        params: входные параметры.
        result: результат действия.
        duration_ms: длительность в миллисекундах.
        nest_level: уровень вложенности.

    Возвращает:
        GlobalFinishEvent с заполненными полями.
    """
    return GlobalFinishEvent(
        action_class=action_class,
        action_name=action_name,
        nest_level=nest_level,
        context=context or _TEST_CONTEXT,
        params=params or _TEST_PARAMS,
        result=result or BaseResult(),
        duration_ms=duration_ms,
    )


def make_global_start_event(
    *,
    action_name: str = _TEST_ACTION_NAME,
    action_class: type = _TEST_ACTION_CLASS,
    context: Context | None = None,
    params: BaseParams | None = None,
    nest_level: int = 1,
) -> GlobalStartEvent:
    """
    Создаёт GlobalStartEvent без эмиссии — для тестов get_handlers().

    Возвращает:
        GlobalStartEvent с заполненными полями.
    """
    return GlobalStartEvent(
        action_class=action_class,
        action_name=action_name,
        nest_level=nest_level,
        context=context or _TEST_CONTEXT,
        params=params or _TEST_PARAMS,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Плагины для test_handlers.py
# ═════════════════════════════════════════════════════════════════════════════

class CounterPlugin(Plugin):
    """
    Минимальный плагин-счётчик.

    Один обработчик GlobalFinishEvent для всех действий. Инкрементирует
    state["count"] при каждом вызове. ignore_exceptions=False —
    критический обработчик, ошибка пробрасывается.
    """

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_count(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["count"] += 1
        return state


class DualHandlerPlugin(Plugin):
    """
    Плагин с двумя обработчиками на одно событие (GlobalFinishEvent).

    on_handler_a инкрементирует state["a"] на 1.
    on_handler_b инкрементирует state["b"] на 10.
    Оба ignore_exceptions=False — последовательное выполнение.
    """

    async def get_initial_state(self) -> dict:
        return {"a": 0, "b": 0}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_handler_a(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["a"] += 1
        return state

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_handler_b(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["b"] += 10
        return state


class CustomInitPlugin(Plugin):
    """
    Плагин с параметризованным начальным состоянием.

    Принимает initial_value в конструкторе. get_initial_state() возвращает
    {"value": initial_value}. Обработчик on_increment добавляет 1 к value.
    """

    def __init__(self, initial_value: int = 100):
        self._initial_value = initial_value

    async def get_initial_state(self) -> dict:
        return {"value": self._initial_value}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_increment(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["value"] += 1
        return state


# ═════════════════════════════════════════════════════════════════════════════
# Плагины для test_emit.py
# ═════════════════════════════════════════════════════════════════════════════

class RecordingPlugin(Plugin):
    """
    Плагин-записыватель.

    Записывает тип события и action_name в state["events"]
    при каждом GlobalFinishEvent. Используется для проверки,
    что emit_event доставляет события и поля корректны.
    """

    async def get_initial_state(self) -> dict:
        return {"events": []}

    @on(GlobalFinishEvent)
    async def on_record(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["events"].append({
            "event_type": type(event).__name__,
            "action_name": event.action_name,
            "nest_level": event.nest_level,
            "duration_ms": event.duration_ms,
        })
        return state


class SelectivePlugin(Plugin):
    """
    Плагин с фильтром action_name_pattern.

    Реагирует только на действия, содержащие "Order" в полном имени.
    Используется для проверки, что action_name_pattern фильтрует события.
    """

    async def get_initial_state(self) -> dict:
        return {"order_events": []}

    @on(GlobalFinishEvent, action_name_pattern=".*Order.*")
    async def on_order_event(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["order_events"].append(event.action_name)
        return state


# ═════════════════════════════════════════════════════════════════════════════
# Плагины для test_find_plugin.py
# ═════════════════════════════════════════════════════════════════════════════

class AlphaPlugin(Plugin):
    """
    Плагин с обработчиком GlobalFinishEvent — реагирует на все действия.
    """

    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalFinishEvent)
    async def on_finish(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        return state


class BetaPlugin(Plugin):
    """
    Плагин с обработчиком GlobalFinishEvent с action_name_pattern=".*Order.*".

    Реагирует только на действия, содержащие "Order" в полном имени класса.
    """

    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalFinishEvent, action_name_pattern=".*Order.*")
    async def on_order_finish(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        return state


class GammaPlugin(Plugin):
    """
    Плагин с обработчиком GlobalStartEvent (не GlobalFinishEvent).

    Используется для проверки, что поиск по GlobalFinishEvent не возвращает
    обработчики, подписанные на GlobalStartEvent.
    """

    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalStartEvent)
    async def on_start(self, state: dict, event: GlobalStartEvent, log) -> dict:
        return state


class MultiEventPlugin(Plugin):
    """
    Плагин с тремя обработчиками на разные события и фильтры.

    on_start: GlobalStartEvent для всех действий.
    on_finish: GlobalFinishEvent для всех действий.
    on_order_finish: GlobalFinishEvent для действий с "Order" в имени.

    Для GlobalFinishEvent + "*OrderAction" должны найтись два обработчика
    (on_finish и on_order_finish). Для GlobalFinishEvent + "PingAction" —
    один (on_finish). Для GlobalStartEvent + любое действие — один (on_start).
    """

    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalStartEvent)
    async def on_start(self, state: dict, event: GlobalStartEvent, log) -> dict:
        return state

    @on(GlobalFinishEvent)
    async def on_finish(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        return state

    @on(GlobalFinishEvent, action_name_pattern=".*Order.*")
    async def on_order_finish(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        return state


# ═════════════════════════════════════════════════════════════════════════════
# Плагины для test_exceptions.py
# ═════════════════════════════════════════════════════════════════════════════

class IgnoredErrorPlugin(Plugin):
    """
    Плагин с ignore_exceptions=True, который мутирует state перед raise.

    Мутирует state["before_error"]=True, затем бросает RuntimeError.
    ignore_exceptions=True — ошибка подавляется, но in-place мутация
    state видна (state — мутабельный dict, передаётся по ссылке).
    """

    async def get_initial_state(self) -> dict:
        return {"before_error": False, "after_error": False}

    @on(GlobalFinishEvent, ignore_exceptions=True)
    async def on_error_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["before_error"] = True
        raise RuntimeError("Ignored error")
        # state["after_error"] = True  # не выполнится


class PropagatedErrorPlugin(Plugin):
    """
    Плагин с ignore_exceptions=False, выбрасывающий RuntimeError.

    Ошибка пробрасывается наружу через emit_event().
    """

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_strict_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        raise RuntimeError("Strict error must propagate")


class CustomExceptionPlugin(Plugin):
    """
    Плагин с ignore_exceptions=False, выбрасывающий CustomPluginError.

    Проверяет, что тип кастомного исключения сохраняется при пробросе.
    """

    async def get_initial_state(self) -> dict:
        return {}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_custom_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        raise CustomPluginError("Custom plugin error")


class SuccessAfterFailPlugin(Plugin):
    """
    Плагин с успешным обработчиком. ignore_exceptions=False.

    Используется для проверки, что исключение критического плагина
    прерывает выполнение (этот плагин не должен получить управление
    если предыдущий критический плагин упал).
    """

    async def get_initial_state(self) -> dict:
        return {"count": 0}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_success_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["count"] += 1
        return state


# ═════════════════════════════════════════════════════════════════════════════
# Плагины для test_concurrency.py
# ═════════════════════════════════════════════════════════════════════════════

class SlowParallelPlugin(Plugin):
    """
    Плагин с задержкой 0.1с. ignore_exceptions=True.

    При наличии нескольких таких плагинов PluginRunContext выбирает
    параллельную стратегию (asyncio.gather). Общее время ≈ 0.1с,
    а не 0.1с × N.
    """

    async def get_initial_state(self) -> dict:
        return {"executed": False}

    @on(GlobalFinishEvent, ignore_exceptions=True)
    async def on_slow_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        await asyncio.sleep(0.1)
        state["executed"] = True
        return state


class SlowSequentialPlugin(Plugin):
    """
    Плагин с задержкой 0.1с. ignore_exceptions=False.

    При наличии хотя бы одного такого плагина PluginRunContext выбирает
    последовательную стратегию. Общее время ≈ 0.1с × N.
    """

    async def get_initial_state(self) -> dict:
        return {"executed": False}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_slow_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        await asyncio.sleep(0.1)
        state["executed"] = True
        return state


# ═════════════════════════════════════════════════════════════════════════════
# Плагины для test_concurrency.py (параметризованные задержки)
# ═════════════════════════════════════════════════════════════════════════════

class SlowPluginIgnore(Plugin):
    """
    Плагин с параметризованной задержкой. ignore_exceptions=True.

    При наличии нескольких таких плагинов PluginRunContext выбирает
    параллельную стратегию (asyncio.gather). Общее время ≈ max(delay),
    а не sum(delay).
    """

    def __init__(self, delay: float = 0.05):
        self._delay = delay

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on(GlobalFinishEvent, ignore_exceptions=True)
    async def on_slow_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        await asyncio.sleep(self._delay)
        state["calls"].append("slow")
        return state


class FastPluginIgnore(Plugin):
    """
    Плагин без задержки. ignore_exceptions=True.

    Используется вместе с SlowPluginIgnore для проверки, что быстрый
    плагин завершается вместе с медленными при параллельном выполнении.
    """

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on(GlobalFinishEvent, ignore_exceptions=True)
    async def on_fast_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        state["calls"].append("fast")
        return state


class SlowPluginNoIgnore(Plugin):
    """
    Плагин с параметризованной задержкой. ignore_exceptions=False.

    Наличие хотя бы одного такого плагина переключает PluginRunContext
    на последовательную стратегию. Общее время ≈ sum(delay).
    """

    def __init__(self, delay: float = 0.05):
        self._delay = delay

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on(GlobalFinishEvent, ignore_exceptions=False)
    async def on_slow_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        await asyncio.sleep(self._delay)
        state["calls"].append("slow")
        return state


class FailingPluginIgnore(Plugin):
    """
    Плагин, выбрасывающий RuntimeError. ignore_exceptions=True.

    Ошибка подавляется, остальные плагины продолжают работу.
    Используется для проверки, что падающий плагин не прерывает
    параллельное выполнение.
    """

    async def get_initial_state(self) -> dict:
        return {"calls": []}

    @on(GlobalFinishEvent, ignore_exceptions=True)
    async def on_failing_handler(self, state: dict, event: GlobalFinishEvent, log) -> dict:
        raise RuntimeError("Plugin intentionally failed")
