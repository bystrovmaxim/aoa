# src/action_machine/checkers/result_date_checker.py
"""
Чекер для полей с датой в результате аспекта.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что поле результата является объектом datetime или строкой,
разбираемой по указанному формату. Поддерживает проверку диапазона дат
(min_date, max_date).

═══════════════════════════════════════════════════════════════════════════════
ДВОЙНОЕ ИСПОЛЬЗОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

1. Как декоратор метода-аспекта (порядок с @regular_aspect не важен):

    @regular_aspect("Проверка даты")
    @ResultDateChecker("created_at", date_format="%Y-%m-%d")
    async def check_date(self, ...):
        return {"created_at": "2024-01-15"}

2. Как валидатор результата (вызывается машиной):

    checker = ResultDateChecker("created_at", date_format="%Y-%m-%d")
    checker.check({"created_at": "2024-01-15"})

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТРЫ КОНСТРУКТОРА
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — имя поля в словаре результата аспекта.
    required : bool — обязательно ли поле. По умолчанию True.
    date_format : str | None — формат строки даты (например, "%Y-%m-%d").
                  Обязателен, если значение поля — строка.
    min_date : datetime | None — минимально допустимая дата (включительно).
    max_date : datetime | None — максимально допустимая дата (включительно).

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    ValidationFieldError — значение не datetime и не строка;
                           строка не соответствует формату;
                           дата вне допустимого диапазона.
"""

from datetime import datetime
from typing import Any

from action_machine.core.exceptions import ValidationFieldError

from .result_field_checker import ResultFieldChecker


class ResultDateChecker(ResultFieldChecker):
    """
    Проверяет, что значение является датой (datetime или строка с форматом).

    Поддерживает двойной режим: декоратор метода-аспекта и валидатор dict.
    При использовании как декоратор записывает _checker_meta в функцию,
    включая дополнительные параметры date_format, min_date, max_date.
    """

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        date_format: str | None = None,
        min_date: datetime | None = None,
        max_date: datetime | None = None,
    ):
        """
        Инициализирует чекер.

        Аргументы:
            field_name: имя поля в словаре результата аспекта.
            required: обязательно ли поле. По умолчанию True.
            date_format: формат строки даты (например, "%Y-%m-%d"). Обязателен,
                         если значение поля — строка. Параметр назван date_format
                         вместо format, чтобы не перекрывать встроенную функцию.
            min_date: минимально допустимая дата (включительно).
            max_date: максимально допустимая дата (включительно).
        """
        super().__init__(field_name, required)
        self.date_format = date_format
        self.min_date = min_date
        self.max_date = max_date

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Возвращает дополнительные параметры чекера дат.

        Эти параметры попадают в _checker_meta при использовании как декоратор
        и затем передаются в конструктор при создании экземпляра машиной
        в ActionProductMachine._apply_checkers().

        Возвращает:
            dict с ключами date_format, min_date, max_date.
        """
        return {
            "date_format": self.date_format,
            "min_date": self.min_date,
            "max_date": self.max_date,
        }

    def _parse_string(self, value: str) -> datetime:
        """
        Разбирает строку в datetime по заданному формату.

        Аргументы:
            value: строка с датой.

        Возвращает:
            Объект datetime.

        Исключения:
            ValidationFieldError: если формат не задан или строка не соответствует формату.
        """
        if self.date_format is None:
            raise ValidationFieldError(
                f"Поле '{self.field_name}' содержит строку, но для разбора "
                f"требуется указать формат даты (параметр date_format)"
            )
        try:
            return datetime.strptime(value, self.date_format)
        except ValueError as exc:
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть строкой даты, "
                f"соответствующей формату '{self.date_format}'"
            ) from exc

    def _check_range(self, value: datetime) -> None:
        """
        Проверяет, что дата находится в допустимом диапазоне.

        Аргументы:
            value: объект datetime для проверки.

        Исключения:
            ValidationFieldError: если дата вне диапазона.
        """
        if self.min_date is not None and value < self.min_date:
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть не меньше {self.min_date}"
            )
        if self.max_date is not None and value > self.max_date:
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть не больше {self.max_date}"
            )

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет тип (datetime или строка) и применяет ограничения диапазона.

        Если значение — строка, разбирает её через _parse_string.
        Если значение — datetime, использует напрямую.
        Иначе — ValidationFieldError.

        Аргументы:
            value: значение для проверки (гарантированно не None).

        Исключения:
            ValidationFieldError: при ошибке типа, формата или диапазона.
        """
        if isinstance(value, str):
            dt_value = self._parse_string(value)
        elif isinstance(value, datetime):
            dt_value = value
        else:
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должен быть объектом datetime или строкой, "
                f"получен {type(value).__name__}"
            )
        self._check_range(dt_value)
