# src/action_machine/checkers/result_int_checker.py
"""
Чекер для целочисленных полей результата аспекта.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что поле результата является целым числом (int) и лежит
в заданном диапазоне.

═══════════════════════════════════════════════════════════════════════════════
ДВОЙНОЕ ИСПОЛЬЗОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

1. Как декоратор метода-аспекта (порядок с @regular_aspect не важен):

    @regular_aspect("Подсчёт")
    @ResultIntChecker("count", required=True, min_value=0, max_value=100)
    async def count_items(self, ...):
        return {"count": 42}

2. Как валидатор результата (вызывается машиной):

    checker = ResultIntChecker("count", min_value=0)
    checker.check({"count": 42})

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТРЫ КОНСТРУКТОРА
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — имя поля в словаре результата аспекта.
    required : bool — обязательно ли поле. По умолчанию True.
    min_value : int | None — минимально допустимое значение (включительно).
    max_value : int | None — максимально допустимое значение (включительно).

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    ValidationFieldError — значение не int; значение вне диапазона.
"""

from typing import Any

from action_machine.core.exceptions import ValidationFieldError

from .result_field_checker import ResultFieldChecker


class ResultIntChecker(ResultFieldChecker):
    """
    Проверяет, что значение является целым числом и лежит в заданном диапазоне.

    Поддерживает двойной режим: декоратор метода-аспекта и валидатор dict.
    При использовании как декоратор записывает _checker_meta в функцию,
    включая дополнительные параметры min_value, max_value.
    """

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        min_value: int | None = None,
        max_value: int | None = None,
    ):
        """
        Инициализирует чекер.

        Аргументы:
            field_name: имя поля в словаре результата аспекта.
            required: обязательно ли поле. По умолчанию True.
            min_value: минимально допустимое значение (включительно).
            max_value: максимально допустимое значение (включительно).
        """
        super().__init__(field_name, required)
        self.min_value = min_value
        self.max_value = max_value

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Возвращает дополнительные параметры целочисленного чекера.

        Эти параметры попадают в _checker_meta при использовании как декоратор
        и затем передаются в конструктор при создании экземпляра машиной
        в ActionProductMachine._apply_checkers().

        Возвращает:
            dict с ключами min_value, max_value.
        """
        return {
            "min_value": self.min_value,
            "max_value": self.max_value,
        }

    def _validate_int(self, value: Any) -> int:
        """
        Проверяет, что значение является целым числом, и возвращает его.

        Аргументы:
            value: значение для проверки.

        Возвращает:
            value как int.

        Исключения:
            ValidationFieldError: если value не int.
        """
        if not isinstance(value, int):
            raise ValidationFieldError(
                f"Параметр '{self.field_name}' должен быть целым числом, получен {type(value).__name__}"
            )
        return value

    def _check_range(self, value: int) -> None:
        """
        Проверяет, что целое число находится в допустимом диапазоне.

        Аргументы:
            value: значение для проверки.

        Исключения:
            ValidationFieldError: если число вне диапазона.
        """
        if self.min_value is not None and value < self.min_value:
            raise ValidationFieldError(
                f"Параметр '{self.field_name}' должен быть не меньше {self.min_value}"
            )
        if self.max_value is not None and value > self.max_value:
            raise ValidationFieldError(
                f"Параметр '{self.field_name}' должен быть не больше {self.max_value}"
            )

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет тип (int) и применяет ограничения диапазона.

        Аргументы:
            value: значение для проверки (гарантированно не None).

        Исключения:
            ValidationFieldError: при нарушении типа или диапазона.
        """
        int_value = self._validate_int(value)
        self._check_range(int_value)
