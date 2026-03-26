"""
Чекер для строковых полей результата аспекта.

Назначение:
    Проверяет, что поле результата является строкой и удовлетворяет условиям:
    - not_empty: строка не пустая.
    - min_length: минимальная длина.
    - max_length: максимальная длина.

Двойное использование:
    1. Как декоратор метода-аспекта (порядок с @regular_aspect не важен):
        @regular_aspect("Валидация")
        @ResultStringChecker("name", "Имя пользователя", required=True, min_length=3)
        async def validate(self, ...):
            return {"name": "John"}

    2. Как валидатор результата (вызывается машиной):
        checker = ResultStringChecker("name", "Имя пользователя", required=True)
        checker.check({"name": "John"})
"""

from typing import Any

from action_machine.core.exceptions import ValidationFieldError

from .result_field_checker import ResultFieldChecker


class ResultStringChecker(ResultFieldChecker):
    """
    Проверяет, что значение является строкой и соответствует заданным ограничениям.

    Поддерживает двойной режим: декоратор метода-аспекта и валидатор dict.
    При использовании как декоратор записывает _checker_meta в функцию,
    включая дополнительные параметры min_length, max_length, not_empty.
    """

    def __init__(
        self,
        field_name: str,
        desc: str,
        required: bool = True,
        min_length: int | None = None,
        max_length: int | None = None,
        not_empty: bool = False,
    ):
        """
        Инициализирует чекер.

        Аргументы:
            field_name: имя поля.
            desc: описание чекера (обязательно).
            required: обязательно ли поле.
            min_length: минимальная допустимая длина строки (включительно).
            max_length: максимальная допустимая длина строки (включительно).
            not_empty: если True, строка не может быть пустой (len>0).
        """
        super().__init__(field_name, required, desc)
        self.min_length = min_length
        self.max_length = max_length
        self.not_empty = not_empty

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Возвращает дополнительные параметры строкового чекера.

        Эти параметры попадают в _checker_meta при использовании как декоратор
        и затем передаются в конструктор при создании экземпляра машиной
        в ActionProductMachine._apply_checkers().

        Возвращает:
            dict с ключами min_length, max_length, not_empty.
        """
        return {
            "min_length": self.min_length,
            "max_length": self.max_length,
            "not_empty": self.not_empty,
        }

    def _validate_string_type(self, value: Any) -> str:
        """
        Проверяет, что значение является строкой, и возвращает его.

        Аргументы:
            value: проверяемое значение.

        Возвращает:
            Значение, приведённое к строке.

        Исключения:
            ValidationFieldError: если value не строка.
        """
        if not isinstance(value, str):
            raise ValidationFieldError(
                f"Параметр '{self.field_name}' должен быть строкой, получен {type(value).__name__}"
            )
        return value

    def _check_empty(self, value: str) -> None:
        """
        Проверяет, что строка не пустая (если установлен флаг not_empty).

        Аргументы:
            value: строка для проверки.

        Исключения:
            ValidationFieldError: если строка пуста.
        """
        if self.not_empty and len(value) == 0:
            raise ValidationFieldError(f"Параметр '{self.field_name}' не может быть пустым")

    def _check_length(self, value: str) -> None:
        """
        Проверяет длину строки на соответствие min_length и max_length.

        Аргументы:
            value: строка для проверки.

        Исключения:
            ValidationFieldError: если длина вне допустимого диапазона.
        """
        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationFieldError(
                f"Длина параметра '{self.field_name}' должна быть не меньше {self.min_length}"
            )
        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationFieldError(
                f"Длина параметра '{self.field_name}' должна быть не больше {self.max_length}"
            )

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Выполняет полную проверку: тип, пустоту (если требуется), длину.

        Аргументы:
            value: значение для проверки.
        """
        str_value = self._validate_string_type(value)
        self._check_empty(str_value)
        self._check_length(str_value)
