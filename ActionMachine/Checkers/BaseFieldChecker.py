from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Union, Type, Optional
from ActionMachine.Core.Exceptions import ValidationFieldException

class BaseFieldChecker(ABC):
    def __init__(self, field_name: str, required: bool, desc: str) -> None:
        self.field_name = field_name
        self.required = required
        self.desc = desc

    def __call__(self, target: Union[Type[Any], Callable[..., Any]]) -> Union[Type[Any], Callable[..., Any]]:
        if isinstance(target, type):
            if not hasattr(target, '_field_checkers'):
                target._field_checkers = []  # type: ignore
            target._field_checkers.append(self)  # type: ignore
        elif callable(target):
            if not hasattr(target, '_result_checkers'):
                target._result_checkers = []  # type: ignore
            target._result_checkers.append(self)  # type: ignore
        else:
            raise TypeError("Декоратор может применяться только к классам или методам")
        return target

    @abstractmethod
    def _check_type_and_constraints(self, value: Any) -> None:
        pass

    def check(self, params: Dict[str, Any]) -> None:
        value = params.get(self.field_name)
        if self.required and value is None:
            raise ValidationFieldException(
                f"Отсутствует обязательный параметр: '{self.field_name}'",
                field=self.field_name
            )
        if not self.required and value is None:
            return
        try:
            self._check_type_and_constraints(value)
        except ValidationFieldException as e:
            if not e.field:
                e.field = self.field_name
            raise