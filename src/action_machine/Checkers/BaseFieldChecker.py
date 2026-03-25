# ActionMachine/Checkers/BaseFieldChecker.py
"""
Базовый класс для всех чекеров полей.

Чекер может использоваться как декоратор:
- для класса: добавляет себя в список _field_checkers класса (валидация входных параметров).
- для метода: добавляет себя в список _result_checkers метода (проверка результата).

При применении к классу декоратор проверяет, что класс наследует CheckerGateHost,
который объявляет атрибут _field_checkers. Если нет — выбрасывает TypeError.
Это гарантирует, что декоратор не добавляет динамических атрибутов —
все поля объявлены в миксине.

При применении к методу декоратор добавляет временный атрибут _result_checkers
к функции. Это нормальный паттерн для декораторов методов — у функций нет миксинов.
Атрибут собирается и удаляется в CheckerGateHost.__init_subclass__.

Все конкретные чекеры (IntFieldChecker, StringFieldChecker и т.д.) наследуются от
BaseFieldChecker и переопределяют метод _check_type_and_constraints.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from action_machine.Core.Exceptions import ValidationFieldError


class BaseFieldChecker(ABC):
    """
    Абстрактный базовый класс для всех чекеров полей.

    Чекер может использоваться как декоратор:
    - для класса: добавляет себя в список _field_checkers класса (валидация входных параметров).
    - для метода: добавляет себя в список _result_checkers метода (проверка результата).

    Атрибуты:
        field_name: имя поля, которое проверяет данный чекер.
        required: является ли поле обязательным.
        desc: описание чекера.
    """

    def __init__(self, field_name: str, required: bool, desc: str) -> None:
        """
        Инициализирует чекер.

        Аргументы:
            field_name: имя поля, которое будет проверяться.
            required: если True, поле считается обязательным; при отсутствии значения
                      будет выброшено исключение ValidationFieldError.
            desc: описание чекера.
        """
        self.field_name = field_name
        self.required = required
        self.desc = desc

    def __call__(self, target: type[Any] | Callable[..., Any]) -> type[Any] | Callable[..., Any]:
        """
        Позволяет использовать экземпляр чекера как декоратор для класса или метода.

        - Если target — класс, проверяет наличие миксина CheckerGateHost
          и добавляет чекер в атрибут _field_checkers класса.
        - Если target — метод (функция), добавляет чекер в атрибут _result_checkers метода.
          Это временный атрибут, который собирается в CheckerGateHost.__init_subclass__.

        Аргументы:
            target: декорируемый объект (класс или метод).

        Возвращает:
            тот же объект target (без изменений).

        Исключения:
            TypeError: если target — класс, не наследующий CheckerGateHost.
            TypeError: если target не является классом и не является вызываемым объектом.
        """
        if isinstance(target, type):
            # Импорт внутри метода — чтобы избежать циклического импорта.
            from action_machine.Checkers.checker_gate_host import (
                CheckerGateHost,  # pylint: disable=import-outside-toplevel
            )

            if not issubclass(target, CheckerGateHost):
                raise TypeError(
                    f"Checker decorator can only be applied to classes inheriting CheckerGateHost. "
                    f"Class {target.__name__} does not inherit CheckerGateHost. "
                    f"Ensure the class inherits from BaseAction or CheckerGateHost directly."
                )

            # _field_checkers объявлен в CheckerGateHost как ClassVar,
            # поэтому после issubclass-проверки атрибут гарантированно существует.
            target._field_checkers.append(self)
        elif callable(target):
            # Для методов: _result_checkers — временный атрибут на функции.
            # У функций нет миксинов, это нормальный паттерн.
            # Атрибут собирается и удаляется в CheckerGateHost.__init_subclass__.
            if not hasattr(target, "_result_checkers"):
                target._result_checkers = []  # type: ignore[attr-defined]
            target._result_checkers.append(self)  # type: ignore[attr-defined]
        else:
            raise TypeError("Декоратор может применяться только к классам или методам")
        return target

    @abstractmethod
    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Абстрактный метод, обязательный к переопределению в наследниках.
        Должен проверять тип значения и дополнительные ограничения.
        """
        pass

    def _check_required(self, value: Any) -> bool:
        """
        Проверяет обязательность поля и наличие значения.

        Аргументы:
            value: значение поля.

        Возвращает:
            True, если проверка обязательности пройдена и значение присутствует (или поле необязательно).

        Исключения:
            ValidationFieldError: если поле обязательно, но значение отсутствует.
        """
        if self.required and value is None:
            raise ValidationFieldError(
                f"Отсутствует обязательный параметр: '{self.field_name}'", field=self.field_name
            )
        return not self.required or value is not None

    def check(self, params: dict[str, Any]) -> None:
        """
        Выполняет проверку значения поля в словаре параметров (или результата).

        Последовательность действий:
        1. Извлекает значение по field_name из params.
        2. Проверяет обязательность.
        3. Если поле необязательное и отсутствует – завершает проверку.
        4. Иначе вызывает _check_type_and_constraints.
        5. Если вложенная проверка выбрасывает исключение без поля, добавляет имя поля.

        Аргументы:
            params: словарь с параметрами.

        Исключения:
            ValidationFieldError: при нарушении любого условия проверки.
        """
        value = params.get(self.field_name)

        if not self._check_required(value):
            return

        try:
            self._check_type_and_constraints(value)
        except ValidationFieldError as e:
            if not e.field:
                e.field = self.field_name
            raise