# src/action_machine/checkers/result_instance_checker.py
"""
Чекер для проверки принадлежности значения указанному классу и функция-декоратор result_instance.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Модуль содержит два компонента:

1. **ResultInstanceChecker** — класс чекера. Проверяет, что поле результата
   является экземпляром указанного класса (или одного из классов, если
   передан кортеж). Создаётся машиной из CheckerMeta при выполнении аспекта.

2. **result_instance** — функция-декоратор. Применяется к методу-аспекту
   и записывает метаданные чекера в атрибут ``_checker_meta`` метода.
   MetadataBuilder собирает эти метаданные в ClassMetadata.checkers.

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ КАК ДЕКОРАТОР
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Получение пользователя")
    @result_instance("user", User, required=True)
    async def get_user(self, params, state, box, connections):
        return {"user": User(id=1, name="John")}

═══════════════════════════════════════════════════════════════════════════════
ИСПОЛЬЗОВАНИЕ МАШИНОЙ
═══════════════════════════════════════════════════════════════════════════════

    checker = ResultInstanceChecker("user", User)
    checker.check({"user": User(id=1, name="John")})  # OK

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТРЫ
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
from .result_string_checker import _build_checker_meta


class ResultInstanceChecker(ResultFieldChecker):
    """
    Проверяет, что значение является экземпляром указанного класса
    (или одного из классов, если передан кортеж).

    Создаётся машиной из CheckerMeta при выполнении аспекта.

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

        Эти параметры сохраняются в CheckerMeta.extra_params при сборке
        метаданных и передаются в конструктор при создании экземпляра
        машиной в ActionProductMachine._apply_checkers().

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


# ═════════════════════════════════════════════════════════════════════════════
# Функция-декоратор
# ═════════════════════════════════════════════════════════════════════════════


def result_instance(
    field_name: str,
    expected_class: type[Any] | tuple[type[Any], ...],
    required: bool = True,
) -> Any:
    """
    Декоратор метода-аспекта. Объявляет поле-экземпляр класса в результате аспекта.

    Записывает метаданные чекера в атрибут ``_checker_meta`` метода.
    MetadataBuilder собирает эти метаданные в ClassMetadata.checkers.
    Машина создаёт экземпляр ResultInstanceChecker из CheckerMeta
    и вызывает checker.check(result_dict) при выполнении аспекта.

    Аргументы:
        field_name: имя поля в словаре результата аспекта.
        expected_class: класс (или кортеж классов), которым должно
                       соответствовать значение.
        required: обязательно ли поле. По умолчанию True.

    Возвращает:
        Декоратор, записывающий _checker_meta в метод.

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
