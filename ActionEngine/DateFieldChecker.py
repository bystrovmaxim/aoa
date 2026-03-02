from typing import Any, Optional
from datetime import datetime
from .BaseFieldChecker import BaseFieldChecker
from .Exceptions import ValidationFieldException

class DateFieldChecker(BaseFieldChecker):
    def __init__(self,
                 field_name: str,
                 required: bool = True,
                 format: Optional[str] = None,
                 min_date: Optional[datetime] = None,
                 max_date: Optional[datetime] = None):
        super().__init__(field_name, required)
        self.format = format
        self.min_date = min_date
        self.max_date = max_date

    def _check_type_and_constraints(self, value: Any) -> None:
        if isinstance(value, str):
            if not self.format:
                raise ValidationFieldException(
                    f"Параметр '{self.field_name}': для строкового ввода требуется формат"
                )
            try:
                dt = datetime.strptime(value, self.format)
            except ValueError:
                raise ValidationFieldException(
                    f"Параметр '{self.field_name}' должен быть строкой даты, соответствующей формату '{self.format}'"
                )
        elif isinstance(value, datetime):
            dt = value
        else:
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть объектом datetime или строкой, получен {type(value).__name__}"
            )

        if self.min_date is not None and dt < self.min_date:
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть не меньше {self.min_date}"
            )

        if self.max_date is not None and dt > self.max_date:
            raise ValidationFieldException(
                f"Параметр '{self.field_name}' должен быть не больше {self.max_date}"
            )