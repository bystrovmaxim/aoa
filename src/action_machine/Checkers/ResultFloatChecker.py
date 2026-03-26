"""
Чекер для полей с плавающей точкой результата аспекта.

Назначение:
    Проверяет, что поле результата является числом (int или float) и лежит в заданном диапазоне.

Использование:
    Применяется как декоратор к методам-аспектам:
        @regular_aspect("Расчёт цены")
        @ResultFloatChecker("price", "Цена", required=True, min_value=0.0)
        async def calculate_price(self, ...):
            return {"price": 99.99}
"""

from typing import Any

from action_machine.Core.Exceptions import ValidationFieldError

from .ResultFieldChecker import ResultFieldChecker


class ResultFloatChecker(ResultFieldChecker):
    """
    Проверяет, что значение является числом (int или float) и лежит в заданном диапазоне.
    """

    def __init__(
        self,
        field_name: str,
        desc: str,
        required: bool = True,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> None:
        """
        Инициализирует чекер.

        Аргументы:
            field_name: имя поля.
            desc: описание чекера (обязательно).
            required: обязательно ли поле.
            min_value: минимально допустимое значение (включительно).
            max_value: максимально допустимое значение (включительно).
        """
        super().__init__(field_name, required, desc)
        self.min_value = min_value
        self.max_value = max_value

    def _validate_number(self, value: Any) -> float:
        """
        Проверяет, что значение является числом (int или float), и возвращает его как float.

        Аргументы:
            value: значение для проверки.

        Возвращает:
            value, приведённое к float.

        Исключения:
            ValidationFieldException: если value не число.
        """
        if not isinstance(value, (int, float)):
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть числом, получен {type(value).__name__}"
            )
        return float(value)

    def _check_range(self, value: float) -> None:
        """
        Проверяет, что число находится в допустимом диапазоне.

        Аргументы:
            value: значение для проверки.

        Исключения:
            ValidationFieldException: если число вне диапазона.
        """
        if self.min_value is not None and value < self.min_value:
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть не меньше {self.min_value}"
            )
        if self.max_value is not None and value > self.max_value:
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть не больше {self.max_value}"
            )

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет тип и применяет ограничения.
        """
        num_value = self._validate_number(value)
        self._check_range(num_value)