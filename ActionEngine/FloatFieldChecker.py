from typing import Any, Optional
from .BaseFieldChecker import BaseFieldChecker
from .Exceptions import ValidationFieldException

class FloatFieldChecker(BaseFieldChecker):
    def __init__(self,
                 field_name: str,
                 required: bool = True,
                 min_value: Optional[float] = None,
                 max_value: Optional[float] = None):
        super().__init__(field_name, required)
        self.min_value = min_value
        self.max_value = max_value

    def _check_type_and_constraints(self, value: Any) -> None:
        if not isinstance(value, (int, float)):
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть числом, получен {type(value).__name__}"
            )

        if self.min_value is not None and value < self.min_value:
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть не меньше {self.min_value}"
            )

        if self.max_value is not None and value > self.max_value:
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть не больше {self.max_value}"
            )