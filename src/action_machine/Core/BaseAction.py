# ActionMachine/Core/BaseAction.py
"""
Базовый класс для всех действий ActionMachine.

Действия параметризованы типами Params и Result, которые должны
соответствовать протоколам ReadableDataProtocol и WritableDataProtocol.

Аспекты действий (регулярные и summary) определяются в наследниках
с помощью декораторов @aspect и @summary_aspect из модуля AspectMethod.
BaseAction не содержит методов аспектов — только общую инфраструктуру.

Аспекты принимают параметр state типа BaseState (вместо dict[str, Any]),
что обеспечивает единообразный интерфейс (resolve, get, write, items)
и контролируемую запись.

Пример:
    >>> @CheckRoles(CheckRoles.ADMIN, desc="Создание заказа")
    ... class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):
    ...     @summary_aspect("Формирование результата")
    ...     async def summary(self, params, state, deps, connections):
    ...         return CreateOrderResult(order_id=state["order_id"])
"""

from abc import ABC
from typing import Any, Generic, TypeVar

from action_machine.Core.Protocols import ReadableDataProtocol, WritableDataProtocol

# Дженерик-параметры для типизации действия.
# P ограничен ReadableDataProtocol — параметры только для чтения.
# R ограничен WritableDataProtocol — результат для чтения и записи.
P = TypeVar("P", bound=ReadableDataProtocol)
R = TypeVar("R", bound=WritableDataProtocol)


class BaseAction(ABC, Generic[P, R]):  # noqa: UP046
    """
    Базовое действие.

    Наследники определяют аспекты с помощью декораторов @aspect и @summary_aspect.
    Не содержит состояния — все данные передаются через params и state (объект BaseState).

    Атрибуты класса:
        _dependencies:    список зависимостей, зарегистрированных
                          декоратором @depends. Каждый элемент — словарь
                          с описанием зависимости.
        _full_class_name: кешированное полное имя класса.
                          None до первого вызова get_full_class_name.
    """

    _dependencies: list[dict[str, Any]] = []
    _full_class_name: str | None = None

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
            cls: type = self.__class__
            module: str = cls.__module__ or ""
            self._full_class_name = f"{module}.{cls.__qualname__}"
        return self._full_class_name