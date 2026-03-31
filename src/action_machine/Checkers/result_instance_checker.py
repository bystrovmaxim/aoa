# src/action_machine/checkers/result_instance_checker.py
"""
Чекер для проверки, что значение результата является экземпляром указанного класса.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Проверяет, что поле результата является экземпляром указанного класса
(или одного из классов, если передан кортеж).

═══════════════════════════════════════════════════════════════════════════════
ДВОЙНОЕ ИСПОЛЬЗОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

1. Как декоратор метода-аспекта (порядок с @regular_aspect не важен):

    @regular_aspect("Получение пользователя")
    @ResultInstanceChecker("user", User, required=True)
    async def get_user(self, ...):
        return {"user": User(id=1, name="John")}

2. Как валидатор результата (вызывается машиной):

    checker = ResultInstanceChecker("user", User)
    checker.check({"user": User(id=1, name="John")})

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТРЫ КОНСТРУКТОРА
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — имя поля в словаре результата аспекта.
    expected_class : type | tuple[type, ...] — класс (или кортеж классов),
                     которым должно соответствовать значение.
    required : bool — обязательно ли поле. По умолчанию True.

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    ValidationFieldError — значение не является экземпляром ожидаемого класса.
"""

from typing import Any

from action_machine.core.exceptions import ValidationFieldError

from .result_field_checker import ResultFieldChecker


class ResultInstanceChecker(ResultFieldChecker):
    """
    Проверяет, что значение является экземпляром указанного класса
    (или одного из классов, если передан кортеж).

    Поддерживает двойной режим: декоратор метода-аспекта и валидатор dict.
    При использовании как декоратор записывает _checker_meta в функцию,
    включая дополнительный параметр expected_class.
    """

    def __init__(
        self,
        field_name: str,
        expected_class: type[Any] | tuple[type[Any], ...],
        required: bool = True,
    ) -> None:
        """
        Инициализирует чекер.

        Аргументы:
            field_name: имя поля в словаре результата аспекта.
            expected_class: класс (или кортеж классов), которым должно
                           соответствовать значение.
            required: является ли поле обязательным. По умолчанию True.
        """
        super().__init__(field_name, required)
        self.expected_class = expected_class

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Возвращает дополнительные параметры чекера экземпляров.

        Эти параметры попадают в _checker_meta при использовании как декоратор
        и затем передаются в конструктор при создании экземпляра машиной
        в ActionProductMachine._apply_checkers().

        Возвращает:
            dict с ключом expected_class.
        """
        return {
            "expected_class": self.expected_class,
        }

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет, что value является экземпляром ожидаемого класса
        (или одного из классов в кортеже).

        Аргументы:
            value: значение для проверки (гарантированно не None).

        Исключения:
            ValidationFieldError: если value не является экземпляром ожидаемого класса.
        """
        if not isinstance(value, self.expected_class):
            if isinstance(self.expected_class, tuple):
                names = ", ".join(cls.__name__ for cls in self.expected_class)
                raise ValidationFieldError(
                    f"Поле '{self.field_name}' должно быть экземпляром одного из классов: {names}, "
                    f"получен {type(value).__name__}"
                )
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть экземпляром класса {self.expected_class.__name__}, "
                f"получен {type(value).__name__}"
            )
