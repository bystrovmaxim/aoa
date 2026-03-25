"""
Базовый класс для всех действий ActionMachine.

Действия параметризованы типами Params и Result, которые должны
соответствовать протоколам ReadableDataProtocol и WritableDataProtocol.

Аспекты действий (регулярные и summary) определяются в наследниках
с помощью декораторов @regular_aspect и @summary_aspect из модуля aspects.
BaseAction не содержит методов аспектов — только общую инфраструктуру.

Аспекты принимают параметр state типа BaseState (вместо dict[str, Any]),
что обеспечивает единообразный интерфейс (resolve, get, write, items)
и контролируемую запись.

Управление метаданными (роли, зависимости, чекеры, аспекты) осуществляется через
шлюзы (gates), которые присоединяются к классу через миксины:
- RoleGateHost – для ролевой спецификации (декоратор @CheckRoles)
- DependencyGateHost – для зависимостей (декоратор @depends)
- CheckerGateHost – для чекеров полей (декораторы чекеров)
- AspectGateHost – для аспектов (декораторы @regular_aspect, @summary_aspect)

Все шлюзы создаются на уровне класса, замораживаются после сборки
и предоставляют единый интерфейс для доступа к метаданным.

Пример:
    >>> @CheckRoles(CheckRoles.ADMIN, desc="Создание заказа")
    ... class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):
    ...     @summary_aspect("Формирование результата")
    ...     async def summary(self, params, state, box, connections):
    ...         return CreateOrderResult(order_id=state["order_id"])
"""

from abc import ABC
from typing import Any, ClassVar, Generic, TypeVar

from action_machine.aspects.aspect_gate_host import AspectGateHost
from action_machine.Auth.role_gate_host import RoleGateHost
from action_machine.Checkers.checker_gate_host import CheckerGateHost
from action_machine.Core.Protocols import ReadableDataProtocol, WritableDataProtocol
from action_machine.dependencies.dependency_gate_host import DependencyGateHost

# Дженерик-параметры для типизации действия.
# P ограничен ReadableDataProtocol — параметры только для чтения.
# R ограничен WritableDataProtocol — результат для чтения и записи.
P = TypeVar("P", bound=ReadableDataProtocol)
R = TypeVar("R", bound=WritableDataProtocol)


class BaseAction(
    ABC,
    RoleGateHost,
    DependencyGateHost,
    CheckerGateHost,
    AspectGateHost,
    Generic[P, R],
):
    """
    Базовое действие.

    Наследники определяют аспекты с помощью декораторов @regular_aspect и @summary_aspect.
    Не содержит состояния — все данные передаются через params и state (объект BaseState).

    Метаданные (роли, зависимости, чекеры, аспекты) собираются автоматически
    при создании класса через миксины. Доступ к ним осуществляется через методы:
    - get_role_gate() → RoleGate
    - get_dependency_gate() → DependencyGate
    - get_checker_gate() → CheckerGate
    - get_aspects() → (regular_aspects, summary_aspect)

    Атрибуты класса (устаревшие, будут удалены после миграции):
        _dependencies:    список зависимостей (заменён на DependencyGate)
        _full_class_name: кешированное полное имя класса.
                          None до первого вызова get_full_class_name.
        _connections:     список объявленных соединений (через @connection)
    """

    # Устаревшие атрибуты для обратной совместимости, будут удалены
    _dependencies: ClassVar[list[dict[str, Any]]] = []
    _connections: ClassVar[list[dict[str, Any]]] = []   # временно, пока нет ConnectionGate
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