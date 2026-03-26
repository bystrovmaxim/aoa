# src/action_machine/Core/BaseAction.py
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

Управление метаданными (роли, зависимости, чекеры, аспекты, соединения)
осуществляется через GateCoordinator и ClassMetadata. Машина
(ActionProductMachine) получает метаданные через свой экземпляр
координатора: self._coordinator.get(action.__class__).

Миксины RoleGateHost, DependencyGateHost, CheckerGateHost, AspectGateHost,
ConnectionGateHost являются маркерами — они разрешают применение
соответствующих декораторов (@CheckRoles, @depends, чекеры,
@regular_aspect/@summary_aspect, @connection) и не содержат логики.

Пример:
    >>> @CheckRoles(CheckRoles.NONE, desc="No authentication")
    ... class PingAction(BaseAction[BaseParams, BaseResult]):
    ...     @summary_aspect("Pong response")
    ...     async def summary(self, params, state, box, connections):
    ...         return BaseResult(message="pong")
"""

from abc import ABC

from action_machine.aspects.aspect_gate_host import AspectGateHost

# Маркерные миксины — разрешают применение соответствующих декораторов
from action_machine.auth.role_gate_host import RoleGateHost
from action_machine.checkers.checker_gate_host import CheckerGateHost
from action_machine.core.protocols import ReadableDataProtocol, WritableDataProtocol
from action_machine.dependencies.dependency_gate_host import DependencyGateHost
from action_machine.resource_managers.connection_gate_host import ConnectionGateHost


class BaseAction[P: ReadableDataProtocol, R: WritableDataProtocol](
    ABC,
    RoleGateHost,
    DependencyGateHost[object],
    CheckerGateHost,
    AspectGateHost,
    ConnectionGateHost,
):
    """
    Базовое действие.

    Наследники определяют аспекты с помощью декораторов @regular_aspect
    и @summary_aspect. Не содержит состояния — все данные передаются
    через params и state (объект BaseState).

    Метаданные (роли, зависимости, чекеры, аспекты, соединения) собираются
    автоматически при первом обращении к классу через GateCoordinator.
    Доступ к метаданным осуществляется через координатор машины:
        metadata = machine._coordinator.get(action.__class__)

    BaseAction НЕ содержит метода get_metadata() и НЕ обращается к
    GateCoordinator напрямую. Координатор — ответственность машины.

    Атрибуты класса:
        _full_class_name: кешированное полное имя класса.
                          None до первого вызова get_full_class_name.
    """

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
