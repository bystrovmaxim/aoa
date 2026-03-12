# ActionMachine/Checkers/BaseFieldChecker.py
"""
Базовый класс для всех чекеров полей.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Union, Type

from ActionMachine.Core.Exceptions import ValidationFieldException

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
                      будет выброшено исключение ValidationFieldException.
            desc: описание чекера.
        """
        self.field_name = field_name
        self.required = required
        self.desc = desc

    def __call__(self, target: Union[Type[Any], Callable[..., Any]]) -> Union[Type[Any], Callable[..., Any]]:
        """
        Позволяет использовать экземпляр чекера как декоратор для класса или метода.

        - Если target — класс, добавляет чекер в атрибут _field_checkers класса.
        - Если target — метод (функция), добавляет чекер в атрибут _result_checkers метода.

        Аргументы:
            target: декорируемый объект (класс или метод).

        Возвращает:
            тот же объект target (без изменений).

        Исключения:
            TypeError: если target не является классом и не является вызываемым объектом.
        """
        if isinstance(target, type):
            if not hasattr(target, '_field_checkers'):
                target._field_checkers = []  # type: ignore
            target._field_checkers.append(self)  # type: ignore
        elif callable(target):
            if not hasattr(target, '_result_checkers'):
                target._result_checkers = []  # type: ignore
            target._result_checkers.append(self)  # type: ignore
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
            ValidationFieldException: если поле обязательно, но значение отсутствует.
        """
        if self.required and value is None:
            raise ValidationFieldException(
                f"Отсутствует обязательный параметр: '{self.field_name}'",
                field=self.field_name
            )
        return not self.required or value is not None

    def check(self, params: Dict[str, Any]) -> None:
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
            ValidationFieldException: при нарушении любого условия проверки.
        """
        value = params.get(self.field_name)

        if not self._check_required(value):
            return

        try:
            self._check_type_and_constraints(value)
        except ValidationFieldException as e:
            if not e.field:
                e.field = self.field_name
            raise