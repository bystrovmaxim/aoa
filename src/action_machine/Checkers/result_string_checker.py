# src/action_machine/checkers/result_string_checker.py
"""
Чекер для строковых полей результата аспекта и функция-декоратор result_string.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит два компонента:

1. **ResultStringChecker** — класс чекера. Проверяет, что поле результата
   является строкой и удовлетворяет условиям: not_empty, min_length, max_length.
   Создаётся машиной из CheckerMeta при выполнении аспекта.

2. **result_string** — функция-декоратор. Применяется к методу-аспекту
   и записывает метаданные чекера в атрибут ``_checker_meta`` метода.
   MetadataBuilder собирает эти метаданные в ClassMetadata.checkers.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ КАК ДЕКОРАТОР
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Валидация")
    @result_string("name", required=True, min_length=3)
    async def validate(self, params, state, box, connections):
        return {"name": "John"}

Порядок с @regular_aspect не важен — оба декоратора записывают разные
атрибуты в одну функцию.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ МАШИНОЙ
═══════════════════════════════════════════════════════════════════════════════

    # ActionProductMachine._apply_checkers() создаёт экземпляр:
    checker = ResultStringChecker("name", required=True, min_length=3)
    checker.check({"name": "John"})  # OK

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТРЫ
═══════════════════════════════════════════════════════════════════════════════

    field_name : str — имя поля в словаре результата аспекта.
    required : bool — обязательно ли поле. По умолчанию True.
    min_length : int | None — минимальная допустимая длина строки.
    max_length : int | None — максимальная допустимая длина строки.
    not_empty : bool — если True, строка не может быть пустой (len > 0).

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    ValidationFieldError — значение не строка; строка пуста при not_empty;
                           длина вне допустимого диапазона.
"""

from typing import Any

from action_machine.core.exceptions import ValidationFieldError

from .result_field_checker import ResultFieldChecker


class ResultStringChecker(ResultFieldChecker):
    """
    Проверяет, что значение является строкой и соответствует заданным ограничениям.

    Создаётся машиной из CheckerMeta при выполнении аспекта.

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
        Инициализирует чекер.

        Аргументы:
            field_name: имя поля в словаре результата аспекта.
            required: обязательно ли поле. По умолчанию True.
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
        Возвращает дополнительные параметры строкового чекера.

        Эти параметры сохраняются в CheckerMeta.extra_params при сборке
        метаданных и передаются в конструктор при создании экземпляра
        машиной в ActionProductMachine._apply_checkers().

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
            Значение как строка.

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
            value: значение для проверки (гарантированно не None).

        Исключения:
            ValidationFieldError: при любом нарушении ограничений.
        """
        str_value = self._validate_string_type(value)
        self._check_empty(str_value)
        self._check_length(str_value)


# ═════════════════════════════════════════════════════════════════════════════
# Функция-декоратор
# ═════════════════════════════════════════════════════════════════════════════


def result_string(
    field_name: str,
    required: bool = True,
    min_length: int | None = None,
    max_length: int | None = None,
    not_empty: bool = False,
) -> Any:
    """
    Декоратор метода-аспекта. Объявляет строковое поле в результате аспекта.

    Записывает метаданные чекера в атрибут ``_checker_meta`` метода.
    MetadataBuilder собирает эти метаданные в ClassMetadata.checkers.
    Машина создаёт экземпляр ResultStringChecker из CheckerMeta
    и вызывает checker.check(result_dict) при выполнении аспекта.

    Аргументы:
        field_name: имя поля в словаре результата аспекта.
        required: обязательно ли поле. По умолчанию True.
        min_length: минимальная допустимая длина строки (включительно).
        max_length: максимальная допустимая длина строки (включительно).
        not_empty: если True, строка не может быть пустой (len > 0).

    Возвращает:
        Декоратор, записывающий _checker_meta в метод.

    Пример:
        @regular_aspect("Валидация")
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
# Вспомогательная функция построения метаданных
# ═════════════════════════════════════════════════════════════════════════════


def _build_checker_meta(checker: ResultFieldChecker) -> dict[str, Any]:
    """
    Строит словарь метаданных чекера для _checker_meta.

    Содержит все параметры, необходимые MetadataBuilder для создания
    CheckerMeta, а ActionProductMachine._apply_checkers — для создания
    экземпляра чекера.

    Аргументы:
        checker: экземпляр чекера с заполненными параметрами.

    Возвращает:
        dict с ключами: checker_class, field_name, required
        и дополнительными параметрами конкретного чекера.
    """
    result: dict[str, Any] = {
        "checker_class": type(checker),
        "field_name": checker.field_name,
        "required": checker.required,
    }
    result.update(checker._get_extra_params())
    return result
