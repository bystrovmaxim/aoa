################################################################################
# Файл: ActionMachine/Core/ActionTestMachine.py
################################################################################

# ActionMachine/Core/ActionTestMachine.py
"""
Тестовая машина действий с поддержкой моков (асинхронная версия).

Наследует от ActionProductMachine и полностью асинхронна (как и родитель).
Позволяет подменять зависимости через словарь моков.
"""

from typing import Any, Dict, Optional, Type, TypeVar

from ActionMachine.Core.ActionProductMachine import ActionProductMachine
from ActionMachine.Core.DependencyFactory import DependencyFactory
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.MockAction import MockAction
from ActionMachine.Context.Context import Context
from ActionMachine.ResourceManagers.BaseResourceManager import BaseResourceManager

P = TypeVar('P', bound=BaseParams)
R = TypeVar('R', bound=BaseResult)


class ActionTestMachine(ActionProductMachine):
    """
    Тестовая машина с удобным API для подмены зависимостей (асинхронная).

    Принимает в конструкторе словарь моков: {класс: значение}.
    Значение может быть:
    - экземпляром MockAction (будет использован как есть).
    - экземпляром BaseAction (пройдёт через аспектный конвейер).
    - результатом BaseResult (будет обёрнут в MockAction).
    - функцией callable (будет использована как side_effect для MockAction).
    - любым другим объектом (будет возвращён как есть через get()).

    Метод run является асинхронным (как и в родителе).
    Для синхронного использования можно обернуть в asyncio.run().
    """

    def __init__(
        self,
        mocks: Optional[Dict[Type[Any], Any]] = None,
        context: Optional[Context] = None,
    ) -> None:
        """
        Инициализирует тестовую машину.

        Аргументы:
            mocks: словарь подмен {класс_зависимости: значение_мока}.
            context: контекст выполнения (по умолчанию пустой Context).
        """
        super().__init__(context or Context())
        self._mocks = mocks or {}
        self._prepared_mocks: Dict[Type[Any], Any] = {}
        for cls, val in self._mocks.items():
            self._prepared_mocks[cls] = self._prepare_mock(val)

    def _prepare_mock(self, value: Any) -> Any:
        """
        Преобразует переданное значение в объект, пригодный для использования в фабрике.

        Аргументы:
            value: значение мока из словаря.

        Возвращает:
            MockAction, BaseAction или любой другой объект.
        """
        if isinstance(value, MockAction):
            return value
        if isinstance(value, BaseAction):
            return value
        if callable(value):
            return MockAction(side_effect=value)
        if isinstance(value, BaseResult):
            return MockAction(result=value)
        return value

    async def run(
        self,
        action: BaseAction[P, R],
        params: P,
        resources: Optional[Dict[Type[Any], Any]] = None,
        connections: Optional[Dict[str, BaseResourceManager]] = None,
    ) -> R:
        """
        Асинхронно запускает действие. Если action — MockAction, вызывает его напрямую,
        минуя аспектный конвейер. Иначе — стандартное асинхронное выполнение через аспекты.

        Аргументы:
            action: экземпляр действия.
            params: входные параметры.
            resources: словарь внешних ресурсов (передаётся в родительский run).
            connections: словарь ресурсных менеджеров (передаётся в родительский run).

        Возвращает:
            Результат выполнения действия.
        """
        if isinstance(action, MockAction):
            # MockAction.run синхронный, но это нормально внутри асинхронной функции
            return action.run(params)  # type: ignore[return-value]
        return await super().run(action, params, resources=resources, connections=connections)

    def _get_factory(
        self,
        action_class: Type[Any],
        external_resources: Optional[Dict[Type[Any], Any]] = None
    ) -> DependencyFactory:
        """
        Возвращает фабрику зависимостей для класса действия, учитывая моки и внешние ресурсы.

        Приоритет: external_resources > prepared_mocks > стандартные зависимости.
        """
        deps_info = getattr(action_class, '_dependencies', [])
        all_resources = dict(self._prepared_mocks)
        if external_resources:
            all_resources.update(external_resources)  # внешние ресурсы переопределяют моки
        return DependencyFactory(self, deps_info, all_resources)

    def build_factory(self, action_class: Type[Any]) -> DependencyFactory:
        """
        Возвращает фабрику для использования в тестировании отдельных аспектов (без внешних ресурсов).
        """
        return self._get_factory(action_class, external_resources=None)

################################################################################