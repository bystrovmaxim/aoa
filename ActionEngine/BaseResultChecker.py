# Файл: ActionEngine/BaseResultChecker.py
"""
Базовый класс для всех чекеров результата (постусловий).

Требования:
- Документирование всех классов и методов.
- Текст исключений на русском.
- Проверяют словарь result после выполнения аспекта.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from .Exceptions import ValidationFieldException

class BaseResultChecker(ABC):
    """
    Абстрактный базовый класс для проверки результата (словаря).
    Чекер используется как декоратор, навешиваемый на метод аспекта.
    При применении к методу добавляет себя в список _result_checkers этого метода.
    """

    def __call__(self, method):
        """
        Добавляет этот чекер в список _result_checkers декорируемого метода.

        Параметры:
            method: метод, к которому применяется декоратор.

        Возвращает:
            тот же метод (без изменений).
        """
        if not hasattr(method, '_result_checkers'):
            method._result_checkers = []
        method._result_checkers.append(self)
        return method

    @abstractmethod
    def check(self, result: Dict[str, Any]) -> None:
        """
        Проверяет словарь result. При ошибке выбрасывает ValidationFieldException.
        Должен быть переопределён в наследнике.
        """
        pass