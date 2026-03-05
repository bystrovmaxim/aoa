# ActionEngine/Checkers/BaseFieldChecker.py
"""
Базовый класс для всех чекеров полей.

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исключений писать на русском.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Union, Callable
from ActionEngine.Core.Exceptions import ValidationFieldException

class BaseFieldChecker(ABC):
    """
    Абстрактный базовый класс для всех чекеров полей.

    Чекер может использоваться как декоратор:
    - для класса: добавляет себя в список _field_checkers класса (валидация входных параметров).
    - для метода: добавляет себя в список _result_checkers метода (проверка результата).

    Атрибуты:
        field_name (str): имя поля, которое проверяет данный чекер.
        required (bool): является ли поле обязательным.
    """

    def __init__(self, field_name: str, required: bool = True, desc: str = None):
        """
        Инициализирует чекер.

        Параметры:
            field_name: имя поля, которое будет проверяться.
            required: если True, поле считается обязательным; при отсутствии значения
                      будет выброшено исключение ValidationFieldException.
        """
        self.field_name = field_name
        self.required = required
        self.description = desc

    def __call__(self, target: Union[type, Callable]):
        """
        Позволяет использовать экземпляр чекера как декоратор для класса или метода.

        - Если target — класс, добавляет чекер в атрибут _field_checkers класса.
        - Если target — метод (функция), добавляет чекер в атрибут _result_checkers метода.

        Параметры:
            target: декорируемый объект (класс или метод).

        Возвращает:
            тот же объект target (без изменений).

        Исключения:
            TypeError: если target не является классом и не является вызываемым объектом.
        """
        if isinstance(target, type):
            # Декорирование класса: добавляем в _field_checkers
            if '_field_checkers' not in target.__dict__:
                target._field_checkers = []
            target._field_checkers.append(self)
        elif callable(target):
            # Декорирование метода: добавляем в _result_checkers метода
            if not hasattr(target, '_result_checkers'):
                target._result_checkers = []
            target._result_checkers.append(self)
        else:
            raise TypeError("Декоратор может применяться только к классам или методам")
        return target

    @abstractmethod
    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Абстрактный метод, **обязательный к переопределению** в наследниках.
        Должен проверять тип значения и дополнительные ограничения (например, диапазон, длину).
        В случае несоответствия выбрасывает ValidationFieldException с понятным сообщением на русском языке.
        """
        pass

    def check(self, params: Dict[str, Any]) -> None:
        """
        Выполняет проверку значения поля в словаре параметров (или результата).

        Последовательность действий:
        1. Извлекает значение по field_name из params.
        2. Если поле обязательное и значение отсутствует (None) – выбрасывает ValidationFieldException.
        3. Если поле необязательное и значение отсутствует – завершает проверку.
        4. Иначе вызывает _check_type_and_constraints для проверки типа и ограничений.
        5. Если вложенная проверка выбрасывает ValidationFieldException без указания поля,
           добавляет имя поля и пробрасывает исключение дальше.

        Параметры:
            params: словарь с параметрами (может быть входными параметрами или результатом).

        Исключения:
            ValidationFieldException: при нарушении любого условия проверки.
        """
        value = params.get(self.field_name)

        # Проверка обязательности
        if self.required and value is None:
            raise ValidationFieldException(
                f"Отсутствует обязательный параметр: '{self.field_name}'",
                field=self.field_name
            )

        # Если поле необязательное и отсутствует или None, пропускаем
        if not self.required and value is None:
            return

        # Проверка типа и дополнительных ограничений
        try:
            self._check_type_and_constraints(value)
        except ValidationFieldException as e:
            # Если поле не было указано в исключении, добавляем его
            if not e.field:
                e.field = self.field_name
            raise