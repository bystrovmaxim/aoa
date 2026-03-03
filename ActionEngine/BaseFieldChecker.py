# Файл: ActionEngine/BaseFieldChecker.py
"""
Базовый класс для всех чекеров полей.

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исколючений писать на русском.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from .Exceptions import ValidationFieldException

class BaseFieldChecker(ABC):
    """
    Абстрактный базовый класс для всех чекеров полей.

    Чекер используется как декоратор. При применении к классу действия он добавляет себя
    в список _field_checkers этого класса. Во время валидации вызывается метод check(),
    который проверяет наличие и корректность значения поля в переданных параметрах.

    Атрибуты:
        field_name (str): имя поля, которое проверяет данный чекер.
        required (bool): является ли поле обязательным.
    """

    def __init__(self, field_name: str, required: bool = True):
        """
        Инициализирует чекер.

        Параметры:
            field_name: имя поля, которое будет проверяться.
            required: если True, поле считается обязательным; при отсутствии значения
                      будет выброшено исключение ValidationFieldException.
        """
        self.field_name = field_name
        self.required = required

    def __call__(self, cls):
        """
        Позволяет использовать экземпляр чекера как декоратор класса.
        Добавляет себя в атрибут _field_checkers целевого класса, создавая
        независимый список для каждого класса (чтобы избежать смешивания при наследовании).

        Параметры:
            cls: класс, к которому применяется декоратор.

        Возвращает:
            тот же класс cls (с добавленным чекером).
        """
        # Проверяем наличие атрибута именно в словаре класса, а не через hasattr,
        # чтобы не использовать унаследованный список от родителя.
        if '_field_checkers' not in cls.__dict__:
            cls._field_checkers = []
        cls._field_checkers.append(self)
        return cls

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
        Выполняет проверку значения поля в словаре параметров.

        Последовательность действий:
        1. Извлекает значение по field_name из params.
        2. Если поле обязательное и значение отсутствует (None) – выбрасывает ValidationFieldException.
        3. Если поле необязательное и значение отсутствует – завершает проверку.
        4. Иначе вызывает _check_type_and_constraints для проверки типа и ограничений.
        5. Если вложенная проверка выбрасывает ValidationFieldException без указания поля,
           добавляет имя поля и пробрасывает исключение дальше.

        Параметры:
            params: словарь с параметрами, переданными в действие.

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