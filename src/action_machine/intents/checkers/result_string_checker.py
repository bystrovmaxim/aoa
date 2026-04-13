# src/action_machine/intents/checkers/result_string_checker.py
"""
Чекер для строковых полей результата аспекта и функция-декоратор result_string.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит два компонента:

1. **ResultStringChecker** — класс checkerа. Checks, что поле результата
   является строкой и удовлетворяет условиям: not_empty, min_length, max_length.
   Создаётся машиной из checker snapshot entry при выполнении аспекта.

2. **result_string** — функция-декоратор. Применяется к methodу-аспекту
   и записывает метаданные checkerа в атрибут ``_checker_meta`` methodа.
   MetadataBuilder собирает эти метаданные в checker snapshot (GateCoordinator.get_checkers).

═══════════════════════════════════════════════════════════════════════════════
USAGE КАК ДЕКОРАТОР
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Validation")
    @result_string("name", required=True, min_length=3)
    async def validate(self, params, state, box, connections):
        return {"name": "John"}

Порядок с @regular_aspect не важен — оба декоратора записывают разные
атрибуты в одну функцию.

═══════════════════════════════════════════════════════════════════════════════
USAGE МАШИНОЙ
═══════════════════════════════════════════════════════════════════════════════

    # ActionProductMachine._apply_checkers() создаёт экземпляр:
    checker = ResultStringChecker("name", required=True, min_length=3)
    checker.check({"name": "John"})  # OK

═══════════════════════════════════════════════════════════════════════════════
PARAMETERS
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — имя поля в словаре результата аспекта.
    required : bool — required ли поле. По умолчанию True.
    min_length : int | None — минимальная допустимая длина строки.
    max_length : int | None — максимальная допустимая длина строки.
    not_empty : bool — если True, строка не может быть пустой (len > 0).

═══════════════════════════════════════════════════════════════════════════════
ERRORS
═══════════════════════════════════════════════════════════════════════════════

    ValidationFieldError — значение не строка; строка пуста при not_empty;
                           длина вне допустимого диапазона.


AI-CORE-BEGIN
ROLE: module result_string_checker
CONTRACT: Keep runtime behavior unchanged; decorators/inspectors expose metadata consumed by coordinator/machine.
INVARIANTS: Validate declarations early and provide deterministic metadata shape.
FLOW: declarations -> inspector snapshot -> coordinator cache -> runtime usage.
AI-CORE-END
"""

from typing import Any

from action_machine.intents.checkers.result_field_checker import ResultFieldChecker
from action_machine.model.exceptions import ValidationFieldError


class ResultStringChecker(ResultFieldChecker):
    """
    Checks, что значение является строкой и соответствует заданным ограничениям.

    Создаётся машиной из checker snapshot entry при выполнении аспекта.

    Атрибуты:
        min_length : int | None — минимальная допустимая длина строки.
        max_length : int | None — максимальная допустимая длина строки.
        not_empty : bool — если True, строка не может быть пустой.
    """

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        min_length: int | None = None,
        max_length: int | None = None,
        not_empty: bool = False,
    ):
        """
        Инициализирует checker.

        Args:
            field_name: имя поля в словаре результата аспекта.
            required: required ли поле. По умолчанию True.
            min_length: минимальная допустимая длина строки (включительно).
            max_length: максимальная допустимая длина строки (включительно).
            not_empty: если True, строка не может быть пустой (len > 0).
        """
        super().__init__(field_name, required)
        self.min_length = min_length
        self.max_length = max_length
        self.not_empty = not_empty

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Returns дополнительные параметры строкового checkerа.

        Эти параметры сохраняются в snapshot-метаданных checkerа при сборке
        метаданных и передаются в конструктор при создании экземпляра
        машиной в ActionProductMachine._apply_checkers().

        Returns:
            dict с ключами min_length, max_length, not_empty.
        """
        return {
            "min_length": self.min_length,
            "max_length": self.max_length,
            "not_empty": self.not_empty,
        }

    def _validate_string_type(self, value: Any) -> str:
        """
        Checks, что значение является строкой, и возвращает его.

        Args:
            value: проверяемое значение.

        Returns:
            Значение как строка.

        Raises:
            ValidationFieldError: если value не строка.
        """
        if not isinstance(value, str):
            raise ValidationFieldError(
                f"Параметр '{self.field_name}' должен быть строкой, got {type(value).__name__}"
            )
        return value

    def _check_empty(self, value: str) -> None:
        """
        Checks, что строка не пустая (если установлен флаг not_empty).

        Args:
            value: строка для проверки.

        Raises:
            ValidationFieldError: если строка пуста.
        """
        if self.not_empty and len(value) == 0:
            raise ValidationFieldError(f"Параметр '{self.field_name}' не может быть пустым")

    def _check_length(self, value: str) -> None:
        """
        Checks длину строки на соответствие min_length и max_length.

        Args:
            value: строка для проверки.

        Raises:
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

        Args:
            value: значение для проверки (гарантированно не None).

        Raises:
            ValidationFieldError: при любом нарушении ограничений.
        """
        str_value = self._validate_string_type(value)
        self._check_empty(str_value)
        self._check_length(str_value)


# ═════════════════════════════════════════════════════════════════════════════
# Decorator function
# ═════════════════════════════════════════════════════════════════════════════


def result_string(
    field_name: str,
    required: bool = True,
    min_length: int | None = None,
    max_length: int | None = None,
    not_empty: bool = False,
) -> Any:
    """
    Декоратор methodа-аспекта. Объявляет строковое поле в результате аспекта.

    Записывает метаданные checkerа в атрибут ``_checker_meta`` methodа.
    MetadataBuilder собирает эти метаданные в checker snapshot (GateCoordinator.get_checkers).
    Машина создаёт экземпляр ResultStringChecker из checker snapshot entry
    и вызывает checker.check(result_dict) при выполнении аспекта.

    Args:
        field_name: имя поля в словаре результата аспекта.
        required: required ли поле. По умолчанию True.
        min_length: минимальная допустимая длина строки (включительно).
        max_length: максимальная допустимая длина строки (включительно).
        not_empty: если True, строка не может быть пустой (len > 0).

    Returns:
        Декоратор, записывающий _checker_meta в method.

    Пример:
        @regular_aspect("Validation")
        @result_string("validated_user", required=True, min_length=1)
        async def validate(self, params, state, box, connections):
            return {"validated_user": params.user_id}
    """
    checker = ResultStringChecker(
        field_name=field_name,
        required=required,
        min_length=min_length,
        max_length=max_length,
        not_empty=not_empty,
    )
    meta = _build_checker_meta(checker)

    def decorator(func: Any) -> Any:
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []
        func._checker_meta.append(meta)
        return func

    return decorator


# ═════════════════════════════════════════════════════════════════════════════
# Helper metadata builder
# ═════════════════════════════════════════════════════════════════════════════


def _build_checker_meta(checker: ResultFieldChecker) -> dict[str, Any]:
    """
    Строит словарь метаданных checkerа для _checker_meta.

    Содержит все параметры, необходимые MetadataBuilder для создания
    checker snapshot entry, а ActionProductMachine._apply_checkers — для создания
    экземпляра checkerа.

    Args:
        checker: экземпляр checkerа с заполненными параметрами.

    Returns:
        dict с ключами: checker_class, field_name, required
        и дополнительными параметрами конкретного checkerа.
    """
    result: dict[str, Any] = {
        "checker_class": type(checker),
        "field_name": checker.field_name,
        "required": checker.required,
    }
    result.update(checker._get_extra_params())
    return result
