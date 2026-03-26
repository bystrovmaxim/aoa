# src/action_machine/Plugins/__init__.py
"""
Пакет плагинов ActionMachine.

Содержит:
- OnGateHost — маркерный миксин, обозначающий поддержку декоратора @on
  для подписки методов на события машины. Наследуется Plugin.
- Plugin — абстрактный базовый класс плагинов. Каждый плагин хранит
  собственное состояние (state), которое передаётся в обработчики
  и обновляется после каждого вызова.
- PluginEvent — frozen-датакласс, описывающий событие, доставляемое
  обработчику. Содержит имя действия, параметры, состояние аспекта,
  результат, длительность и другие поля.
- PluginCoordinator — координатор, управляющий жизненным циклом плагинов.
  Инициализирует состояния, маршрутизирует события к подписанным методам,
  обрабатывает ошибки согласно ignore_exceptions.
- on — декоратор для подписки async-метода плагина на событие.
  Записывает SubscriptionInfo в method._on_subscriptions.
- SubscriptionInfo — frozen-датакласс с параметрами подписки
  (event_type, action_filter, ignore_exceptions).

Типичный поток:
    1. @on("global_finish", ".*") записывает SubscriptionInfo
       в method._on_subscriptions.
    2. MetadataBuilder.build(PluginClass) читает _on_subscriptions →
       ClassMetadata.subscriptions (tuple[SubscriptionInfo, ...]).
    3. PluginCoordinator при emit_event() находит подписанные методы
       и вызывает их с текущим state и PluginEvent.
"""

from .decorators import SubscriptionInfo, on
from .on_gate_host import OnGateHost
from .plugin import Plugin
from .plugin_coordinator import PluginCoordinator
from .plugin_event import PluginEvent

__all__ = [
    "OnGateHost",
    "Plugin",
    "PluginEvent",
    "PluginCoordinator",
    "on",
    "SubscriptionInfo",
]