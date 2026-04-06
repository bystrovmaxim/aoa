# src/action_machine/plugins/on_gate_host.py
"""
Модуль: OnGateHost — маркерный миксин для декоратора @on.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

OnGateHost — миксин-маркер, который обозначает, что класс поддерживает
декоратор @on для подписки методов на типизированные события ActionMachine.
Используется в классе Plugin и его наследниках.

Наличие OnGateHost в MRO класса документирует контракт:
«этот класс может содержать методы-обработчики событий (@on)».

MetadataBuilder при сборке метаданных проверяет: если класс содержит
методы с _on_subscriptions (подписки через @on), класс обязан
наследовать OnGateHost. Без него — TypeError.

═══════════════════════════════════════════════════════════════════════════════
ТИПОБЕЗОПАСНАЯ ПОДПИСКА
═══════════════════════════════════════════════════════════════════════════════

Декоратор @on принимает класс события из иерархии BasePluginEvent как
первый аргумент. Подписка срабатывает для указанного класса и всех
его наследников через isinstance-проверку в PluginRunContext.

Дополнительные фильтры (action_class, action_name_pattern,
aspect_name_pattern, nest_level, domain, predicate) сужают выборку
с AND-логикой внутри одного @on. OR-логика реализуется между
несколькими @on на одном методе.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class Plugin(OnGateHost):           ← маркер: разрешает @on на методах
        async def get_initial_state(self) -> Any:
            ...

    class CounterPlugin(Plugin):

        async def get_initial_state(self) -> dict:
            return {}

        @on(GlobalFinishEvent, ignore_exceptions=False)
        async def on_count_call(self, state, event: GlobalFinishEvent, log):
            state[event.action_name] = state.get(event.action_name, 0) + 1
            return state

    # Декоратор @on записывает в метод:
    #   method._on_subscriptions = [SubscriptionInfo(
    #       event_class=GlobalFinishEvent,
    #       method_name="on_count_call",
    #       ignore_exceptions=False,
    #   )]

    # MetadataBuilder → collectors.collect_subscriptions(cls)
    #   Обходит vars(cls), находит _on_subscriptions → ClassMetadata.subscriptions.

    # MetadataBuilder → validators.validate_gate_hosts(cls, ...)
    #   Проверяет: есть подписки → issubclass(cls, OnGateHost) → OK.

    # PluginRunContext.emit_event(event):
    #   plugin.get_handlers(event) → находит обработчики по isinstance
    #   _matches_all_filters(event, sub) → проверяет шаги 2–7
    #   handler(plugin, state, event, log) → вызов

═══════════════════════════════════════════════════════════════════════════════
ЕДИНООБРАЗИЕ С ДРУГИМИ ГЕЙТ-МИКСИНАМИ
═══════════════════════════════════════════════════════════════════════════════

Все гейт-миксины ActionMachine следуют одному паттерну: пустой класс
без логики, служащий проверочным маркером для issubclass(). OnGateHost
находится в ряду с RoleGateHost, AspectGateHost, CheckerGateHost,
ActionMetaGateHost, ConnectionGateHost, OnErrorGateHost,
ContextRequiresGateHost и DescribedFieldsGateHost.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Plugin уже наследует OnGateHost — любой плагин поддерживает @on:

    class MetricsPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"total": 0, "errors": 0}

        @on(GlobalFinishEvent)
        async def on_track_total(self, state, event: GlobalFinishEvent, log):
            state["total"] += 1
            return state

        @on(UnhandledErrorEvent)
        async def on_track_errors(self, state, event: UnhandledErrorEvent, log):
            state["errors"] += 1
            return state

        @on(AfterRegularAspectEvent, aspect_name_pattern=r"validate_.*")
        async def on_validation_done(self, state, event: AfterRegularAspectEvent, log):
            await log.info("Валидация завершена: {%var.name}", name=event.aspect_name)
            return state
"""


class OnGateHost:
    """
    Маркерный миксин, обозначающий поддержку декоратора @on.

    Класс, наследующий OnGateHost, может содержать методы, декорированные
    @on для подписки на типизированные события ActionMachine из иерархии
    BasePluginEvent (GlobalStartEvent, GlobalFinishEvent,
    AfterRegularAspectEvent, UnhandledErrorEvent и т.д.).

    MetadataBuilder собирает подписки из method._on_subscriptions
    в ClassMetadata.subscriptions, а PluginRunContext использует их
    для маршрутизации событий через цепочку фильтров.

    Миксин не содержит логики, полей или методов. Его функция —
    документировать контракт и обеспечивать единообразие с другими
    гейт-миксинами.

    Атрибуты уровня класса (создаются динамически декоратором на методах):
        method._on_subscriptions : list[SubscriptionInfo]
            Список объектов SubscriptionInfo, записываемый декоратором @on
            в метод. Каждый объект содержит:
            - event_class: type[BasePluginEvent] — тип события
            - action_class: tuple[type, ...] | None — фильтр по типу действия
            - action_name_pattern: str | None — regex по имени действия
            - aspect_name_pattern: str | None — regex по имени аспекта
            - nest_level: tuple[int, ...] | None — фильтр по вложенности
            - domain: type | None — фильтр по домену
            - predicate: Callable | None — произвольный фильтр
            - ignore_exceptions: bool — подавление ошибок обработчика
            - method_name: str — имя метода-обработчика
            Читается MetadataBuilder при сборке ClassMetadata.subscriptions.
    """

    pass
