# ActionMachine/Core/BaseAction.py
"""
Базовый класс для всех действий в ActionMachine.

Действия не имеют состояния — все данные передаются через params и state.
Наследники определяют свои аспекты с помощью декораторов @aspect и @summary_aspect.
"""

from abc import ABC
from typing import Generic, TypeVar, Any, Dict, List, Optional

from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult

P = TypeVar('P', bound=BaseParams)
R = TypeVar('R', bound=BaseResult)


class BaseAction(Generic[P, R], ABC):
    """
    Базовый класс для всех действий.

    Наследники определяют свои аспекты с помощью декораторов.
    Действия не имеют состояния — все данные передаются через params и state.

    Атрибуты класса:
        _dependencies (List[Dict[str, Any]]): Кэш списока зависимостей, объявленных через декоратор @depends.
            Заполняется автоматически декоратором. Не предназначен для ручного изменения.
        _full_class_name (Optional[str]): Кэш полного имени класса (модуль + имя).
            Вычисляется лениво при первом вызове get_full_class_name().
    """

    _dependencies: List[Dict[str, Any]] = []
    _full_class_name: Optional[str] = None

    def get_full_class_name(self) -> str:
        """
        Возвращает полное имя класса действия (модуль + имя).

        Используется для сопоставления с регулярными выражениями в плагинах,
        чтобы определить, какие обработчики плагинов должны быть вызваны
        для данного действия.

        Результат кэшируется после первого вызова для повышения производительности
        (ленивое кэширование).

        Возвращает:
            Строка вида 'module.path.ClassName'.
        """
        if self._full_class_name is None:
            cls = self.__class__
            module = cls.__module__ or ""
            self._full_class_name = f"{module}.{cls.__qualname__}"
        return self._full_class_name