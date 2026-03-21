# src/action_machine/Plugins/on_gate.py
"""
OnGate – шлюз для управления подписками плагинов (декоратор @on).

Хранит информацию о подписках, создаваемых декоратором @on.
Каждая подписка связывает метод-обработчик с регулярными выражениями
для имени события и имени класса действия, а также флагом ignore_exceptions.

После завершения сборки (в __init_subclass__ плагина) шлюз замораживается,
и любые попытки регистрации или удаления вызывают RuntimeError.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from action_machine.Core.base_gate import BaseGate


@dataclass(frozen=True)
class Subscription:
    """
    Неизменяемая информация об одной подписке плагина.

    Атрибуты:
        method: метод-обработчик (callable, обычно асинхронный).
        event_regex: скомпилированное регулярное выражение для имени события.
        class_regex: скомпилированное регулярное выражение для полного имени класса действия.
        ignore_exceptions: флаг, указывающий, нужно ли игнорировать исключения в обработчике.
    """
    method: Callable[..., Any]
    event_regex: re.Pattern[str]
    class_regex: re.Pattern[str]
    ignore_exceptions: bool


class OnGate(BaseGate[Subscription]):
    """
    Шлюз для управления подписками плагинов.

    Внутреннее хранение:
        _subscriptions: list[Subscription] – список подписок в порядке регистрации.
        _frozen: bool – флаг заморозки.
    """

    def __init__(self) -> None:
        """Инициализирует пустой шлюз подписок."""
        self._subscriptions: list[Subscription] = []
        self._frozen: bool = False

    def _check_frozen(self) -> None:
        """Проверяет, не заморожен ли шлюз. Если заморожен – выбрасывает RuntimeError."""
        if self._frozen:
            raise RuntimeError("OnGate is frozen, cannot modify")

    def register(self, _component: Subscription, **metadata: Any) -> Subscription:
        """
        Регистрирует подписку.

        Аргументы:
            _component: объект Subscription.
            **metadata: не используется, но оставлен для совместимости с BaseGate.

        Возвращает:
            Зарегистрированный компонент.

        Исключения:
            RuntimeError: если шлюз уже заморожен.
        """
        self._check_frozen()
        self._subscriptions.append(_component)
        return _component

    def unregister(self, _component: Subscription) -> None:
        """
        Удаляет подписку по ссылке.

        Аргументы:
            _component: подписка для удаления.

        Исключения:
            RuntimeError: если шлюз уже заморожен.
        """
        self._check_frozen()
        # Линейный поиск по списку, так как подписок обычно немного
        for i, sub in enumerate(self._subscriptions):
            if sub is _component:
                self._subscriptions.pop(i)
                return

    def get_components(self) -> list[Subscription]:
        """
        Возвращает список всех подписок в порядке регистрации.

        Возвращаемый список является копией.

        Возвращает:
            Список объектов Subscription.
        """
        return self._subscriptions.copy()

    # -------------------- Дополнительные методы для удобства --------------------

    def get_handlers(self, event_name: str, action_name: str) -> list[tuple[Callable[..., Any], bool]]:
        """
        Возвращает список обработчиков, подходящих под указанные событие и действие.

        Проходит по всем подпискам в порядке регистрации и проверяет совпадение
        регулярных выражений (fullmatch). Возвращает кортежи (метод, ignore_exceptions).

        Аргументы:
            event_name: имя события (например, 'global_start', 'before:validate').
            action_name: полное имя класса действия (включая модуль).

        Возвращает:
            Список кортежей (метод, ignore_exceptions) в порядке регистрации.
        """
        result: list[tuple[Callable[..., Any], bool]] = []
        for sub in self._subscriptions:
            if sub.event_regex.fullmatch(event_name) and sub.class_regex.fullmatch(action_name):
                result.append((sub.method, sub.ignore_exceptions))
        return result

    def get_all_subscriptions(self) -> list[Subscription]:
        """
        Возвращает список всех подписок (синоним get_components).

        Возвращает:
            Список объектов Subscription (копия).
        """
        return self.get_components()

    def freeze(self) -> None:
        """
        Замораживает шлюз, запрещая дальнейшие изменения.

        Вызывается после завершения сбора подписок в __init_subclass__.
        """
        self._frozen = True