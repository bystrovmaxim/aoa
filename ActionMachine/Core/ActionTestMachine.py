# ActionMachine/Core/ActionTestMachine.py
"""
Тестовая машина действий с поддержкой моков.

Наследует от ActionProductMachine и полностью синхронна (как и родитель).
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

P = TypeVar('P', bound=BaseParams)
R = TypeVar('R', bound=BaseResult)


class ActionTestMachine(ActionProductMachine):
    """
    Тестовая машина с удобным API для подмены зависимостей.

    Принимает в конструкторе словарь моков: {класс: значение}.
    Значение может быть:
        - экземпляром MockAction (будет использован как есть).
        - экземпляром BaseAction (пройдёт через аспектный конвейер).
        - результатом BaseResult (будет обёрнут в MockAction).
        - функцией callable (будет использована как side_effect для MockAction).
        - любым другим объектом (будет возвращён как есть через get()).

    Метод run является синхронным (как и в родителе).
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

    def run(self, action: BaseAction[P, R], params: P) -> R:
        """
        Запускает действие. Если action — MockAction, вызывает его напрямую,
        минуя аспектный конвейер. Иначе — стандартное выполнение через аспекты.

        Аргументы:
            action: экземпляр действия.
            params: входные параметры.

        Возвращает:
            Результат выполнения действия.
        """
        if isinstance(action, MockAction):
            return action.run(params)  # type: ignore[return-value]
        return super().run(action, params)

    def _build_factory(self, action_class: Type[Any]) -> DependencyFactory:
        """
        Строит фабрику для конкретного класса действия, учитывая моки.

        Аргументы:
            action_class: класс действия, для которого строится фабрика.

        Возвращает:
            DependencyFactory (или TestDependencyFactory) с учётом подмен.
        """
        deps_info = getattr(action_class, '_dependencies', [])
        prepared = self._prepared_mocks

        class TestDependencyFactory(DependencyFactory):
            """Фабрика зависимостей, учитывающая моки из тестовой машины."""

            def __init__(
                self, machine: Any, deps_info: Any, prepared_mocks: Any
            ) -> None:
                super().__init__(machine, deps_info)
                self._prepared_mocks = prepared_mocks

            def get(self, klass: Type[Any]) -> Any:
                """Сначала ищет в моках, затем — стандартное поведение."""
                if klass in self._prepared_mocks:
                    return self._prepared_mocks[klass]
                return super().get(klass)

        return TestDependencyFactory(self, deps_info, prepared)

    def _get_factory(self, action_class: Type[Any]) -> DependencyFactory:
        """
        Переопределяем, чтобы строить фабрику с учётом моков и кэшировать её.
        """
        if action_class not in self._factory_cache:
            self._factory_cache[action_class] = self._build_factory(action_class)
        return self._factory_cache[action_class]

    def build_factory(self, action_class: Type[Any]) -> DependencyFactory:
        """
        Возвращает фабрику для использования в тестировании отдельных аспектов.

        Аргументы:
            action_class: класс действия.

        Возвращает:
            DependencyFactory с учётом моков.
        """
        return self._get_factory(action_class)