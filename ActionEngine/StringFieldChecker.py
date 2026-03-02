from typing import Any, Optional
from .BaseFieldChecker import BaseFieldChecker
from .Exceptions import ValidationFieldException

class StringFieldChecker(BaseFieldChecker):
    def __init__(self,
                 field_name: str,
                 required: bool = True,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None,
                 not_empty: bool = False):
        super().__init__(field_name, required)
        self.min_length = min_length
        self.max_length = max_length
        self.not_empty = not_empty

    def _check_type_and_constraints(self, value: Any) -> None:
        if not isinstance(value, str):
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть строкой, получен {type(value).__name__}"
            )

        if self.not_empty and not value:
            raise ValidationFieldException(f"Параметр '{self.field_name}' не может быть пустым")

        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationFieldException(
                f"Длина параметра '{self.field_name}' должна быть не меньше {self.min_length}"
            )

        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationFieldException(
                f"Длина параметра '{self.field_name}' должна быть не больше {self.max_length}"
            )