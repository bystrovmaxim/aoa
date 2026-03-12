from typing import Any, Dict, List, Type
from ActionMachine.Core.BaseActionMachine import BaseActionMachine
from ActionMachine.Core.BaseAction import BaseAction
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.BaseParams import BaseParams

class DependencyFactory:
    def __init__(self, machine: BaseActionMachine, deps_info: List[Dict[str, Any]]) -> None:
        self._machine = machine
        self._deps: Dict[Type[Any], Dict[str, Any]] = {info['class']: info for info in deps_info}
        self._instances: Dict[Type[Any], Any] = {}

    def get(self, klass: Type[Any]) -> Any:
        if klass in self._instances:
            return self._instances[klass]
        if klass not in self._deps:
            raise ValueError(f"Dependency {klass.__name__} not declared in @depends")
        info = self._deps[klass]
        if info['factory']:
            instance = info['factory']()
        else:
            instance = klass()
        self._instances[klass] = instance
        return instance

    def run_action(self, action_class: Type[BaseAction[Any, Any]], params: BaseParams) -> BaseResult:
        instance = self.get(action_class)
        return self._machine.run(instance, params)   # type: ignore