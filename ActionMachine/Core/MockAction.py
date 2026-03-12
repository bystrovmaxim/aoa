from typing import Optional, Callable, Any
from ActionMachine.Core.BaseParams import BaseParams
from ActionMachine.Core.BaseResult import BaseResult
from ActionMachine.Core.BaseAction import BaseAction

class MockAction(BaseAction[BaseParams, BaseResult]):
    def __init__(self,
                 result: Optional[BaseResult] = None,
                 side_effect: Optional[Callable[[BaseParams], BaseResult]] = None) -> None:
        self.result = result
        self.side_effect = side_effect
        self.call_count: int = 0
        self.last_params: Optional[BaseParams] = None

    def run(self, params: BaseParams) -> BaseResult:
        self.call_count += 1
        self.last_params = params
        if self.side_effect:
            return self.side_effect(params)
        if self.result is None:
            raise ValueError("MockAction: neither result nor side_effect provided")
        return self.result