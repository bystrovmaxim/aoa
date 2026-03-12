# ActionMachine/Plugins/Plugin.py
"""
Базовый класс для всех плагинов ActionMachine.

Плагины позволяют расширять функциональность ActionMachine без изменения бизнес-логики.
Они подключаются к событиям жизненного цикла выполнения действия и могут выполнять
произвольные действия: логирование, сбор метрик, аудит, дополнительные проверки безопасности.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, List, Tuple


class Plugin(ABC):
    """
    Абстрактный базовый класс для всех плагинов.

    Каждый плагин должен реализовать метод ``get_initial_state``, возвращающий начальное
    состояние для одного запуска действия. Состояние будет передаваться во все обработчики
    плагина, и каждый обработчик обязан вернуть обновлённое состояние.

    Плагины не должны хранить состояние в атрибутах экземпляра, так как оно должно быть
    изолировано для каждого вызова ``run``. Вместо этого состояние управляется машиной и
    передаётся через параметр ``state_plugin`` в каждый обработчик.

    Методы-обработчики помечаются декоратором ``@on`` из модуля ``Decorators``. Они должны быть
    асинхронными (определены с ``async def``) и принимать строго определённый набор аргументов.

    Пример::

        class LoggingPlugin(Plugin):
            def get_initial_state(self) -> Any:
                return {"timers": {}}

            @on('global_start', '.*', ignore_exceptions=True)
            async def log_start(self, state_plugin, event_name, action_name, params,
                                state_aspect, is_summary, deps, context, result, duration):
                state_plugin["timers"][action_name] = time.time()
                print(f"Action {action_name} started")
                return state_plugin
    """

    @abstractmethod
    def get_initial_state(self) -> Any:
        """
        Возвращает начальное состояние плагина для одного выполнения действия.

        Этот метод вызывается машиной перед первым запуском любого обработчика
        данного плагина в рамках текущего вызова ``run``. Возвращаемое значение
        может быть любого типа (обычно словарь или пользовательский объект).
        Оно будет передано во все обработчики как первый аргумент ``state_plugin``,
        и каждый обработчик должен вернуть новое состояние.

        Возвращает:
            Начальное состояние для данного запуска.
        """
        ...

    def get_handlers(self, event_name: str, class_name: str) -> List[Tuple[Callable[..., Any], bool]]:
        """
        Возвращает список подходящих обработчиков для данного события и класса действия.

        Метод перебирает все методы экземпляра, ищет среди них помеченные декоратором ``@on``,
        и проверяет, соответствуют ли регулярные выражения из подписок переданным
        ``event_name`` и ``class_name``. Если соответствие найдено, метод добавляется в результат
        вместе с флагом ``ignore_exceptions`` из соответствующей подписки.

        Если метод имеет несколько подписок, он добавляется только один раз (первая подходящая).

        Аргументы:
            event_name: имя события (например, 'before:choose_channel').
            class_name: полное имя класса действия (включая модуль и наследование).

        Возвращает:
            Список кортежей (метод-обработчик, ignore_exceptions) для всех подходящих подписок.
        """
        handlers: List[Tuple[Callable[..., Any], bool]] = []
        for method_name in dir(self):
            method = getattr(self, method_name)
            if not callable(method) or not hasattr(method, '_plugin_hooks'):
                continue
            for event_regex, class_regex, ignore_exceptions in method._plugin_hooks:
                if event_regex.fullmatch(event_name) and class_regex.fullmatch(class_name):
                    handlers.append((method, ignore_exceptions))
                    break  # метод уже подходит, не нужно проверять остальные его подписки
        return handlers