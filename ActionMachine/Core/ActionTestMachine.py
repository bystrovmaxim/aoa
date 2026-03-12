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
    def __init__(self, mocks: Optional[Dict[Type[Any], Any]] = None, context: Optional[Context] = None) -> None:
        super().__init__(context or Context())
        self._mocks = mocks or {}
        self._prepared_mocks: Dict[Type[Any], Any] = {}
        for cls, val in self._mocks.items():
            self._prepared_mocks[cls] = self._prepare_mock(val)

    def _prepare_mock(self, value: Any) -> Any:
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
        if isinstance(action, MockAction):
            return action.run(params)          # type: ignore
        return super().run(action, params)

    def _build_factory(self, action_class: Type[Any]) -> DependencyFactory:
        deps_info = getattr(action_class, '_dependencies', [])
        prepared = self._prepared_mocks

        class TestDependencyFactory(DependencyFactory):
            def __init__(self, machine: Any, deps_info: Any, prepared_mocks: Any) -> None:
                super().__init__(machine, deps_info)
                self._prepared_mocks = prepared_mocks

            def get(self, klass: Type[Any]) -> Any:
                if klass in self._prepared_mocks:
                    return self._prepared_mocks[klass]
                return super().get(klass)

        return TestDependencyFactory(self, deps_info, prepared)

    def _get_factory(self, action_class: Type[Any]) -> DependencyFactory:
        if action_class not in self._factory_cache:
            self._factory_cache[action_class] = self._build_factory(action_class)
        return self._factory_cache[action_class]

    def build_factory(self, action_class: Type[Any]) -> DependencyFactory:
        return self._get_factory(action_class)