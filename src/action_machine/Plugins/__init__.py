# src/action_machine/plugins/__init__.py
"""
Пакет плагинов ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит полную подсистему плагинов для ActionMachine. Плагины позволяют
расширять поведение машины без изменения ядра: подсчёт вызовов, метрики,
аудит, логирование побочных эффектов и т.д.

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

- OnGateHost — маркерный миксин, обозначающий поддержку декоратора @on
  для подписки методов на события машины. Наследуется Plugin.

- Plugin — абстрактный базовый класс плагинов. Каждый плагин реализует
  get_initial_state(), возвращающий начальное состояние для одного запроса.
  Состояние передаётся в обработчики и обновляется после каждого вызова.

- PluginEvent — frozen-датакласс, описывающий событие, доставляемое
  обработчику. Содержит имя действия, параметры, состояние аспекта,
  результат, длительность и другие поля.

- PluginCoordinator — stateless-координатор, управляющий списком плагинов.
  Не хранит мутабельного состояния между запросами. Предоставляет
  фабричный метод create_run_context() для создания изолированного
  контекста на каждый вызов run().

- PluginRunContext — изолированный контекст плагинов для одного вызова
  run(). Хранит состояния плагинов, маршрутизирует события к подписанным
  методам, создаёт ScopedLogger для каждого обработчика и передаёт его
  как параметр log.

- on — декоратор для подписки async-метода плагина на событие.
  Записывает SubscriptionInfo в method._on_subscriptions.
  Обработчик обязан иметь сигнатуру (self, state, event, log).

- SubscriptionInfo — frozen-датакласс с параметрами подписки
  (event_type, action_filter, ignore_exceptions).

═══════════════════════════════════════════════════════════════════════════════
СИГНАТУРА ОБРАБОТЧИКОВ
═══════════════════════════════════════════════════════════════════════════════

Все обработчики плагинов обязаны иметь сигнатуру с 4 параметрами:

    async def handler(self, state, event, log) → state

    - self   — экземпляр плагина.
    - state  — текущее per-request состояние плагина.
    - event  — объект PluginEvent с данными о событии.
    - log    — ScopedLogger, привязанный к scope плагина.

Scope логгера плагина содержит поля: machine, mode, plugin, action,
event, nest_level. Все поля доступны в шаблонах через {%scope.*}:

    await log.info("[{%scope.plugin}] Действие {%scope.action} завершено")
    await log.debug("Уровень вложенности: {%scope.nest_level}")

═══════════════════════════════════════════════════════════════════════════════
ЖИЗНЕННЫЙ ЦИКЛ ПЛАГИНОВ В РАМКАХ ОДНОГО ЗАПРОСА
═══════════════════════════════════════════════════════════════════════════════

    1. ActionProductMachine._run_internal() вызывает
       plugin_coordinator.create_run_context().
    2. create_run_context() вызывает get_initial_state() для каждого
       плагина и создаёт PluginRunContext с начальными состояниями.
    3. Все события (global_start, before/after аспектов, global_finish)
       отправляются через plugin_ctx.emit_event().
    4. Машина передаёт в emit_event() ссылку на log_coordinator,
       machine_name и mode — для создания ScopedLogger обработчикам.
    5. PluginRunContext создаёт ScopedLogger для каждого обработчика
       и вызывает handler(plugin, state, event, log).
    6. Каждый обработчик получает текущее состояние и возвращает новое.
    7. По завершении run() контекст уничтожается.

═══════════════════════════════════════════════════════════════════════════════
АККУМУЛЯЦИЯ ДАННЫХ МЕЖДУ ЗАПРОСАМИ
═══════════════════════════════════════════════════════════════════════════════

Фреймворк обеспечивает изоляцию per-request состояния. Если плагину
необходимо накапливать данные между запросами (метрики, счётчики), он
использует внешнее хранилище, переданное через конструктор плагина.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР: ПЛАГИН-СЧЁТЧИК
═══════════════════════════════════════════════════════════════════════════════

    class CounterPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"count": 0}

        @on("global_finish", ".*")
        async def count(self, state, event, log):
            state["count"] += 1
            await log.info("Вызовов: {%var.count}", count=state["count"])
            return state

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР: ПЛАГИН АУДИТА
═══════════════════════════════════════════════════════════════════════════════

    class AuditPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"actions": []}

        @on("global_finish", ".*")
        async def audit(self, state, event, log):
            state["actions"].append(event.action_name)
            await log.info(
                "[{%scope.plugin}] Действие {%scope.action} завершено "
                "за {%var.duration}с на уровне {%scope.nest_level}",
                duration=event.duration,
            )
            return state
"""

from .decorators import SubscriptionInfo, on
from .on_gate_host import OnGateHost
from .plugin import Plugin
from .plugin_coordinator import PluginCoordinator
from .plugin_event import PluginEvent
from .plugin_run_context import PluginRunContext

__all__ = [
    "OnGateHost",
    "Plugin",
    "PluginCoordinator",
    "PluginEvent",
    "PluginRunContext",
    "SubscriptionInfo",
    "on",
]
