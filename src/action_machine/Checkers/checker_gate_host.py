# src/action_machine/Checkers/checker_gate_host.py
"""
CheckerGateHost – миксин для присоединения шлюза чекеров к классу действия.

Этот миксин используется в иерархии BaseAction. Он:
- Создаёт экземпляр CheckerGate для класса (один на класс, разделяется всеми экземплярами).
- Собирает информацию о чекерах из декораторов, применённых к классу (валидация параметров)
  и к методам (валидация результатов).
- После сбора замораживает шлюз, чтобы гарантировать неизменность набора чекеров.
- Предоставляет метод get_checker_gate() для доступа к шлюзу из машины.

Механизм сбора:
    Чекеры для класса: собираются из атрибута _field_checkers (создаётся декораторами,
    применёнными к классу). Каждый чекер регистрируется в шлюзе с target_type='class'.

    Чекеры для методов: собираются из атрибута _result_checkers методов (создаётся
    декораторами, применёнными к методам). Для каждого чекера регистрируется запись
    с target_type='method' и ссылкой на метод.

    Особенность: если метод обёрнут статическим/классовым декоратором, оригинальная функция
    может быть доступна через __func__ (для @staticmethod) или __func__ (для @classmethod).
    Мы пытаемся получить исходную функцию, чтобы корректно сопоставить атрибут _result_checkers.

Важно:
    Шлюз хранится в классовой переменной __checker_gate. При наследовании каждый
    подкласс получает свой собственный шлюз. Для этого в __init_subclass__
    явно сбрасывается __checker_gate = None, чтобы при вызове get_checker_gate()
    создавался новый шлюз для дочернего класса, а не использовался родительский.

Обратная совместимость:
    На время миграции старые атрибуты _field_checkers и _result_checkers продолжают
    существовать и заполняются параллельно. После полного перехода на шлюзы они будут удалены.
"""

from typing import Any, ClassVar

from .BaseFieldChecker import BaseFieldChecker
from .checker_gate import CheckerGate


class CheckerGateHost:
    """
    Миксин, добавляющий классу шлюз чекеров.

    Классовые атрибуты:
        __checker_gate: CheckerGate | None – шлюз, общий для всех экземпляров.
    """

    __checker_gate: ClassVar[CheckerGate | None] = None

    @classmethod
    def get_checker_gate(cls) -> CheckerGate:
        """
        Возвращает шлюз чекеров для данного класса.

        Шлюз создаётся лениво при первом вызове, если ещё не был создан.
        После завершения __init_subclass__ шлюз замораживается.

        Возвращает:
            CheckerGate, связанный с классом.
        """
        if cls.__checker_gate is None:
            cls.__checker_gate = CheckerGate()
        return cls.__checker_gate

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Вызывается при создании подкласса. Собирает чекеры из атрибутов
        _field_checkers (классовые) и _result_checkers методов и регистрирует их в шлюзе.

        Алгоритм:
            1. Вызывает super().__init_subclass__() для поддержки множественного наследования.
            2. Сбрасывает унаследованный шлюз, чтобы дочерний класс получил свой собственный.
            3. Получает шлюз через get_checker_gate().
            4. Если есть атрибут _field_checkers (список чекеров класса), регистрирует
               каждый чекер с target_type='class'.
            5. Обходит все методы класса (через cls.__dict__), ищет у них атрибут _result_checkers,
               регистрирует каждый чекер с target_type='method' и ссылкой на метод.
               Для статических/классовых методов извлекаем исходную функцию (через __func__).
            6. Замораживает шлюз.

        Аргументы:
            **kwargs: передаются в родительский __init_subclass__.
        """
        super().__init_subclass__(**kwargs)

        # Сбрасываем унаследованный шлюз, чтобы дочерний класс создал свой собственный
        cls.__checker_gate = None
        gate = cls.get_checker_gate()

        # Регистрируем классовые чекеры (из _field_checkers)
        if hasattr(cls, "_field_checkers"):
            for checker in cls._field_checkers:
                if isinstance(checker, BaseFieldChecker):
                    gate.register(checker, target_type="class")

        # Регистрируем методные чекеры (из _result_checkers методов)
        # Обходим атрибуты класса, определённые непосредственно в этом классе,
        # чтобы избежать проблем с унаследованными служебными атрибутами.
        for name, attr in cls.__dict__.items():
            # Пропускаем служебные атрибуты (начинающиеся с '__') и не-callable
            if name.startswith('__') or not callable(attr):
                continue

            # Для @staticmethod и @classmethod оригинальная функция хранится в __func__
            actual_method = getattr(attr, '__func__', attr)

            if hasattr(actual_method, "_result_checkers"):
                for checker in actual_method._result_checkers:
                    if isinstance(checker, BaseFieldChecker):
                        gate.register(checker, target_type="method", method=actual_method)

        # Замораживаем шлюз – после этого регистрация невозможна
        gate.freeze()