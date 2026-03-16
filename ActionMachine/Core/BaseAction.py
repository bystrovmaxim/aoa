"""
Базовый класс для всех действий ActionMachine.

Действия параметризованы типами Params и Result, которые должны
соответствовать протоколам ReadableDataProtocol и WritableDataProtocol.
"""

from abc import ABC
from typing import Generic, TypeVar, Any, Optional

from ActionMachine.Core.Protocols import ReadableDataProtocol, WritableDataProtocol

P = TypeVar('P', bound=ReadableDataProtocol)
R = TypeVar('R', bound=WritableDataProtocol)


class BaseAction(Generic[P, R], ABC):
    """
    Базовое действие.

    Наследники определяют аспекты с помощью декораторов @aspect и @summary_aspect.
    Не содержит состояния — все данные передаются через params и state.
    """

    _dependencies: list[dict[str, Any]] = []
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