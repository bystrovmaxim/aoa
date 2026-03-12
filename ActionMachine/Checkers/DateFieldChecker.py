# ActionMachine/Checkers/DateFieldChecker.py
"""
Чекер для полей с датой/временем.

Требования:
- Документирование всех классов.
- Документирование всех методов.
- Текст исключений писать на русском.
"""
from typing import Any, Optional
from datetime import datetime
from .BaseFieldChecker import BaseFieldChecker
from ActionMachine.Core.Exceptions import ValidationFieldException

class DateFieldChecker(BaseFieldChecker):
    """
    Проверяет, что значение является датой/временем.
    Принимает либо объект datetime, либо строку в указанном формате.
    Дополнительно можно задать минимальную и максимальную дату.
    """

    def __init__(self,
                 field_name: str,
                 desc: str,
                 required: bool = True,
                 format: Optional[str] = None,
                 min_date: Optional[datetime] = None,
                 max_date: Optional[datetime] = None):
        """
        Параметры:
            field_name: имя поля.
            desc: описание чекера (обязательно).
            required: обязательно ли поле.
            format: формат строки даты (обязателен, если ожидается строка).
            min_date: минимально допустимая дата.
            max_date: максимально допустимая дата.
        """
        super().__init__(field_name, required, desc)
        self.format = format
        self.min_date = min_date
        self.max_date = max_date

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет тип и диапазон даты.
        Если передана строка, преобразует её по формату.
        При ошибках выбрасывает ValidationFieldException.
        """
        if isinstance(value, str):
            if not self.format:
                raise ValidationFieldException(
                    f"Поле '{self.field_name}': для строкового ввода требуется указать формат даты"
                )
            try:
                dt = datetime.strptime(value, self.format)
            except ValueError:
                raise ValidationFieldException(
                    f"Поле '{self.field_name}' должно быть строкой даты, соответствующей формату '{self.format}'"
                )
        elif isinstance(value, datetime):
            dt = value
        else:
            raise ValidationFieldException(
                f"Поле '{self.field_name}' должен быть объектом datetime или строкой, получен {type(value).__name__}"
            )

        if self.min_date is not None and dt < self.min_date:
            raise ValidationFieldException(
                f"Поле '{self.field_name}' должно быть не меньше {self.min_date.isoformat()}"
            )

        if self.max_date is not None and dt > self.max_date:
            raise ValidationFieldException(
                f"Поле '{self.field_name}' должно быть не больше {self.max_date.isoformat()}"
            )