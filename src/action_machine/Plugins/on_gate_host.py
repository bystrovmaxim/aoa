# src/action_machine/Plugins/on_gate_host.py
"""
OnGateHost – миксин для присоединения шлюза подписок к классу плагина.

Этот миксин используется в иерархии Plugin. Он:
- Создаёт экземпляр OnGate для класса (один на класс, разделяется всеми экземплярами).
- Собирает информацию о подписках из декоратора @on, применённого к методам плагина.
- После сбора замораживает шлюз, чтобы гарантировать неизменность набора подписок.
- Предоставляет метод get_on_gate() для доступа к шлюзу из PluginCoordinator.

Механизм сбора:
    Декоратор @on при применении к методу добавляет в метод временный атрибут
    _on_subscriptions (список кортежей с regex и ignore_exceptions). В __init_subclass__
    плагина эти данные собираются, для каждого создаётся Subscription и регистрируется
    в шлюзе. После регистрации временный атрибут удаляется.

Важно:
    Шлюз хранится в классовой переменной __on_gate. При наследовании каждый
    подкласс получает свой собственный шлюз. Для этого в __init_subclass__
    явно сбрасывается __on_gate = None, чтобы при вызове get_on_gate()
    создавался новый шлюз для дочернего класса, а не использовался родительский.

Обратная совместимость:
    На время миграции старый атрибут _plugin_hooks продолжает существовать
    и заполняется параллельно. После полного перехода на шлюзы старый атрибут
    будет удалён.
"""

import re
from typing import Any, ClassVar

from .on_gate import OnGate, Subscription


class OnGateHost:
    """
    Миксин, добавляющий классу плагина шлюз подписок.

    Классовые атрибуты:
        __on_gate: OnGate | None – шлюз, общий для всех экземпляров.
    """

    __on_gate: ClassVar[OnGate | None] = None

    @classmethod
    def get_on_gate(cls) -> OnGate:
        """
        Возвращает шлюз подписок для данного класса плагина.

        Шлюз создаётся лениво при первом вызове, если ещё не был создан.
        После завершения __init_subclass__ шлюз замораживается.

        Возвращает:
            OnGate, связанный с классом плагина.
        """
        if cls.__on_gate is None:
            cls.__on_gate = OnGate()
        return cls.__on_gate

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Вызывается при создании подкласса плагина. Собирает подписки из временных
        метаданных, прикреплённых к методам, и регистрирует их в шлюзе.

        Алгоритм:
            1. Вызывает super().__init_subclass__() для поддержки множественного наследования.
            2. Сбрасывает унаследованный шлюз, чтобы дочерний класс получил свой собственный.
            3. Получает шлюз через get_on_gate().
            4. Обходит все атрибуты, определённые непосредственно в этом классе (cls.__dict__),
               находит методы с атрибутом _on_subscriptions, регистрирует подписки и удаляет атрибут.
            5. Замораживает шлюз.

        Аргументы:
            **kwargs: передаются в родительский __init_subclass__.
        """
        super().__init_subclass__(**kwargs)

        # Сбрасываем унаследованный шлюз, чтобы дочерний класс создал свой собственный
        cls.__on_gate = None
        gate = cls.get_on_gate()

        # Собираем подписки из методов, определённых непосредственно в этом классе
        for name, method in cls.__dict__.items():
            if callable(method) and hasattr(method, "_on_subscriptions"):
                for event_regex, class_regex, ignore_exceptions in method._on_subscriptions:
                    # Компилируем регулярные выражения, если они ещё не скомпилированы
                    if isinstance(event_regex, str):
                        event_regex = re.compile(event_regex)
                    if isinstance(class_regex, str):
                        class_regex = re.compile(class_regex)
                    sub = Subscription(method, event_regex, class_regex, ignore_exceptions)
                    gate.register(sub)
                # Очищаем временные данные метода
                delattr(method, "_on_subscriptions")

        # Замораживаем шлюз – после этого регистрация невозможна
        gate.freeze()