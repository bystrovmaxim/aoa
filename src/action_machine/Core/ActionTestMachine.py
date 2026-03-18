"""
Тестовая машина действий с поддержкой моков (асинхронная версия).

Наследует от ActionProductMachine и полностью асинхронна (как и родитель).
Позволяет подменять зависимости через словарь моков.

Примечание к рефакторингу:
После выделения PluginCoordinator из ActionProductMachine,
ActionTestMachine не требует изменений в логике — он наследует
от ActionProductMachine, который теперь использует
self._plugin_coordinator вместо прямых вызовов _run_plugins_async.
Единственное изменение — удалён неиспользуемый импорт asyncio
(если был).
"""

from typing import Any, TypeVar, cast

from action_machine.Context.context import Context
from action_machine.Core.ActionProductMachine import ActionProductMachine
from action_machine.Core.BaseAction import BaseAction
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseResult import BaseResult
from action_machine.Core.DependencyFactory import DependencyFactory
from action_machine.Core.MockAction import MockAction
from action_machine.ResourceManagers.BaseResourceManager import BaseResourceManager

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResult)


class ActionTestMachine(ActionProductMachine):
    """
    Тестовая машина с удобным API для подмены зависимостей (асинхронная).

    Принимает в конструкторе словарь моков: {класс: значение}.
    Значение может быть:
    - экземпляром MockAction (будет использован как есть).
    - экземпляром BaseAction (пройдёт через аспектный конвейер).
    - результатом BaseResult (будет обёрнут в MockAction).
    - функцией callable (будет использована как side_effect).
    - любым другим объектом (будет возвращён как есть через get()).

    Метод run является асинхронным (как и в родителе).
    Для синхронного использования можно обернуть в asyncio.run().
    """

    def __init__(
        self,
        mocks: dict[type[Any], Any] | None = None,
        ctx: Context | None = None,
    ) -> None:
        """
        Инициализирует тестовую машину.

        Аргументы:
            mocks: словарь подмен {класс_зависимости: значение_мока}.
            ctx: контекст выполнения (по умолчанию пустой Context).

        Примечание:
            Параметр переименован из `context` в `ctx`, чтобы не затенять
            импортированный класс `context`. Ранее вызов `context()` в
            выражении `context if context is not None else context()`
            приводил к ошибке mypy "None" not callable, потому что
            имя параметра перекрывало имя класса.
        """
        super().__init__(ctx if ctx is not None else Context())
        self._mocks: dict[type[Any], Any] = mocks or {}
        self._prepared_mocks: dict[type[Any], Any] = {}
        for cls, val in self._mocks.items():
            self._prepared_mocks[cls] = self._prepare_mock(val)

    def _prepare_mock(self, value: Any) -> Any:
        """
        Преобразует переданное значение в объект, пригодный
        для использования в фабрике.

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
        resources: dict[type[Any], Any] | None = None,
        connections: dict[str, BaseResourceManager] | None = None,
    ) -> R:
        """
        Асинхронно запускает действие. Если action — MockAction,
        вызывает его напрямую, минуя аспектный конвейер.
        Иначе — стандартное асинхронное выполнение через аспекты.

        Аргументы:
            action: экземпляр действия.
            params: входные параметры.
            resources: словарь внешних ресурсов.
            connections: словарь ресурсных менеджеров.

        Возвращает:
            Результат выполнения действия.
        """
        if isinstance(action, MockAction):
            # MockAction.run возвращает BaseResult, но в контексте теста
            # мы уверены, что он соответствует ожидаемому типу R.
            return cast(R, action.run(params))
        return await super().run(action, params, resources=resources, connections=connections)

    def _get_factory(
        self, action_class: type[Any], external_resources: dict[type[Any], Any] | None = None
    ) -> DependencyFactory:
        """
        Возвращает фабрику зависимостей для класса действия,
        учитывая моки и внешние ресурсы.

        Приоритет: external_resources > prepared_mocks > стандартные зависимости.
        """
        deps_info = getattr(action_class, "_dependencies", [])
        all_resources: dict[type[Any], Any] = dict(self._prepared_mocks)
        if external_resources:
            # Внешние ресурсы переопределяют моки
            all_resources.update(external_resources)
        return DependencyFactory(self, deps_info, all_resources)

    def build_factory(self, action_class: type[Any]) -> DependencyFactory:
        """
        Возвращает фабрику для использования в тестировании отдельных
        аспектов (без внешних ресурсов).
        """
        deps_info = getattr(action_class, "_dependencies", [])
        # Явно указываем тип для параметра
        external_resources: dict[type[Any], Any] | None = None
        return DependencyFactory(self, deps_info, external_resources)