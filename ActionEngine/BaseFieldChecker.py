from abc import ABC, abstractmethod
from typing import Dict, Any
from .Exceptions import ValidationFieldException

class BaseFieldChecker(ABC):
    def __init__(self, field_name: str, required: bool = True):
        self.field_name = field_name
        self.required = required

    def __call__(self, cls):
        if not hasattr(cls, "_field_checkers"):
            cls._field_checkers = []
        cls._field_checkers.append(self)
        return cls

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