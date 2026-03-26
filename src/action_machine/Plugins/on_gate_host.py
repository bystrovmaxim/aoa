# src/action_machine/Plugins/on_gate_host.py
"""
Модуль: OnGateHost — маркерный миксин для декоратора @on.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

OnGateHost — миксин-маркер, который обозначает, что класс поддерживает
декоратор @on для подписки методов на события ActionMachine. Используется
в классе Plugin и его наследниках.

Наличие OnGateHost в MRO класса документирует контракт:
«этот класс может содержать методы-обработчики событий (@on)».

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

    class Plugin(OnGateHost):           ← маркер: разрешает @on на методах
        async def get_initial_state(self) -> Any:
            ...

    class CounterPlugin(Plugin):

        async def get_initial_state(self) -> dict:
            return {}

        @on("global_finish", ".*", ignore_exceptions=False)
        async def count_call(self, state, event):
            state[event.action_name] = state.get(event.action_name, 0) + 1
            return state

    # Декоратор @on записывает в метод:
    #   method._on_subscriptions = [SubscriptionInfo(
    #       event_type="global_finish",
    #       action_filter=".*",
    #       ignore_exceptions=False,
    #   )]

    # MetadataBuilder._collect_subscriptions(cls) обходит MRO, находит
    # методы с _on_subscriptions и собирает их в ClassMetadata.subscriptions.

    # PluginCoordinator использует ClassMetadata.subscriptions для
    # маршрутизации событий к нужным методам плагина.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Plugin уже наследует OnGateHost — любой плагин поддерживает @on:

    class MetricsPlugin(Plugin):
        async def get_initial_state(self) -> dict:
            return {"total": 0, "errors": 0}

        @on("global_finish")
        async def track_total(self, state, event):
            state["total"] += 1
            return state

        @on("global_finish")
        async def track_errors(self, state, event):
            if event.error is not None:
                state["errors"] += 1
            return state

        @on("aspect_before", "CreateOrder.*")
        async def log_order_start(self, state, event):
            print(f"Starting order: {event.action_name}")
            return state

    # Класс без OnGateHost не может содержать @on-обработчики.
    # Декоратор @on сам по себе не проверяет миксин (он работает
    # на уровне функций), но PluginCoordinator ожидает Plugin,
    # а Plugin наследует OnGateHost — контракт соблюдается.
"""


class OnGateHost:
    """
    Маркерный миксин, обозначающий поддержку декоратора @on.

    Класс, наследующий OnGateHost, может содержать методы, декорированные
    @on для подписки на события ActionMachine (global_start, global_finish,
    aspect_before, aspect_after и др.).

    MetadataBuilder собирает подписки из method._on_subscriptions
    в ClassMetadata.subscriptions, а PluginCoordinator использует их
    для маршрутизации событий.

    Миксин не содержит логики, полей или методов. Его функция —
    документировать контракт и обеспечивать единообразие с другими
    гейт-миксинами.

    Атрибуты уровня класса (создаются динамически декоратором на методах):
        method._on_subscriptions : list[SubscriptionInfo]
            Список объектов SubscriptionInfo, записываемый декоратором @on
            в метод. Каждый объект содержит:
            - event_type: str — тип события ("global_finish", ...)
            - action_filter: str — regex-фильтр по имени действия
            - ignore_exceptions: bool — игнорировать ли ошибки обработчика
            Читается MetadataBuilder при сборке ClassMetadata.subscriptions.
    """

    pass