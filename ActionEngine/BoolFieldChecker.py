from typing import Any
from .BaseFieldChecker import BaseFieldChecker
from .Exceptions import ValidationFieldException

class BoolFieldChecker(BaseFieldChecker):
    def _check_type_and_constraints(self, value: Any) -> None:
        if not isinstance(value, bool):
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть булевым, получен {type(value).__name__}"
            )