# src/action_machine/intents/checkers/result_instance_checker.py
"""
Чекер для проверки принадлежности значения указанному классу и функция-декоратор result_instance.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит два компонента:

1. **ResultInstanceChecker** — класс checkerа. Checks, что поле результата
   является экземпляром указанного класса (или одного из классов, если
   передан кортеж). Создаётся машиной из checker snapshot entry при выполнении аспекта.

2. **result_instance** — функция-декоратор. Применяется к methodу-аспекту
   и записывает метаданные checkerа в атрибут ``_checker_meta`` methodа.
   MetadataBuilder собирает эти метаданные в checker snapshot (GateCoordinator.get_checkers).

═══════════════════════════════════════════════════════════════════════════════
USAGE КАК ДЕКОРАТОР
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Получение пользователя")
    @result_instance("user", User, required=True)
    async def get_user(self, params, state, box, connections):
        return {"user": User(id=1, name="John")}

═══════════════════════════════════════════════════════════════════════════════
USAGE МАШИНОЙ
═══════════════════════════════════════════════════════════════════════════════

    checker = ResultInstanceChecker("user", User)
    checker.check({"user": User(id=1, name="John")})  # OK

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — имя поля в словаре результата аспекта.
    expected_class : type | tuple[type, ...] — класс (или кортеж классов),
                     которым должно соответствовать значение.
    required : bool — required ли поле. По умолчанию True.

═══════════════════════════════════════════════════════════════════════════════
ERRORS
═══════════════════════════════════════════════════════════════════════════════

    ValidationFieldError — значение не является экземпляром ожидаемого класса.


AI-CORE-BEGIN
ROLE: module result_instance_checker
CONTRACT: Keep runtime behavior unchanged; decorators/inspectors expose metadata consumed by coordinator/machine.
INVARIANTS: Validate declarations early and provide deterministic metadata shape.
FLOW: declarations -> inspector snapshot -> coordinator cache -> runtime usage.
AI-CORE-END
"""

from typing import Any

from action_machine.intents.checkers.result_field_checker import ResultFieldChecker
from action_machine.intents.checkers.result_string_checker import _build_checker_meta
from action_machine.model.exceptions import ValidationFieldError


class ResultInstanceChecker(ResultFieldChecker):
    """
    Checks, что значение является экземпляром указанного класса
    (или одного из классов, если передан кортеж).

    Создаётся машиной из checker snapshot entry при выполнении аспекта.

    Атрибуты:
        expected_class : type | tuple[type, ...] — ожидаемый класс или кортеж классов.
    """

    def __init__(
        self,
        field_name: str,
        expected_class: type[Any] | tuple[type[Any], ...],
        required: bool = True,
    ) -> None:
        """
        Инициализирует checker.

        Args:
            field_name: имя поля в словаре результата аспекта.
            expected_class: класс (или кортеж классов), которым должно
                           соответствовать значение.
            required: является ли поле обязательным. По умолчанию True.
        """
        super().__init__(field_name, required)
        self.expected_class = expected_class

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Returns дополнительные параметры checkerа экземпляров.

        Эти параметры сохраняются в snapshot-метаданных checkerа при сборке
        метаданных и передаются в конструктор при создании экземпляра
        машиной в ActionProductMachine._apply_checkers().

        Returns:
            dict с ключом expected_class.
        """
        return {
            "expected_class": self.expected_class,
        }

    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Checks, что value является экземпляром ожидаемого класса
        (или одного из классов в кортеже).

        Args:
            value: значение для проверки (гарантированно не None).

        Raises:
            ValidationFieldError: если value не является экземпляром ожидаемого класса.
        """
        if not isinstance(value, self.expected_class):
            if isinstance(self.expected_class, tuple):
                names = ", ".join(cls.__name__ for cls in self.expected_class)
                raise ValidationFieldError(
                    f"Поле '{self.field_name}' должно быть экземпляром одного из классов: {names}, "
                    f"got {type(value).__name__}"
                )
            raise ValidationFieldError(
                f"Поле '{self.field_name}' должно быть экземпляром класса {self.expected_class.__name__}, "
                f"got {type(value).__name__}"
            )


# ═════════════════════════════════════════════════════════════════════════════
# Decorator function
# ═════════════════════════════════════════════════════════════════════════════


def result_instance(
    field_name: str,
    expected_class: type[Any] | tuple[type[Any], ...],
    required: bool = True,
) -> Any:
    """
    Декоратор methodа-аспекта. Объявляет поле-экземпляр класса в результате аспекта.

    Записывает метаданные checkerа в атрибут ``_checker_meta`` methodа.
    MetadataBuilder собирает эти метаданные в checker snapshot (GateCoordinator.get_checkers).
    Машина создаёт экземпляр ResultInstanceChecker из checker snapshot entry
    и вызывает checker.check(result_dict) при выполнении аспекта.

    Args:
        field_name: имя поля в словаре результата аспекта.
        expected_class: класс (или кортеж классов), которым должно
                       соответствовать значение.
        required: required ли поле. По умолчанию True.

    Returns:
        Декоратор, записывающий _checker_meta в method.

    Пример:
        @regular_aspect("Получение пользователя")
        @result_instance("user", User, required=True)
        async def get_user(self, params, state, box, connections):
            return {"user": User(id=1, name="John")}

        # Несколько допустимых классов:
        @regular_aspect("Получение данных")
        @result_instance("data", (dict, list), required=True)
        async def get_data(self, params, state, box, connections):
            return {"data": {"key": "value"}}
    """
    checker = ResultInstanceChecker(
        field_name=field_name,
        expected_class=expected_class,
        required=required,
    )
    meta = _build_checker_meta(checker)

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator
