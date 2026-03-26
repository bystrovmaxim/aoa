# src/action_machine/Checkers/ResultFieldChecker.py
"""
Базовый абстрактный чекер для полей результата аспекта.

Назначение:
    Определяет общий интерфейс для всех чекеров полей. Каждый конкретный
    чекер (ResultStringChecker, ResultIntChecker и т.д.) наследует
    ResultFieldChecker и реализует метод _check_type_and_constraints.

Двойное использование:
    ResultFieldChecker и его наследники поддерживают два режима работы:

    1. Как декоратор метода-аспекта:
       Применяется к async-методу и записывает _checker_meta в функцию.
       Порядок с @regular_aspect/@summary_aspect не имеет значения.

           @regular_aspect("Обработка")
           @ResultStringChecker("txn_id", "ID транзакции", required=True)
           async def process(self, params, state, box, connections):
               return {"txn_id": "abc"}

       или

           @ResultStringChecker("txn_id", "ID транзакции", required=True)
           @regular_aspect("Обработка")
           async def process(self, params, state, box, connections):
               return {"txn_id": "abc"}

    2. Как валидатор результата (вызов экземпляра с dict):
       Вызывается машиной (ActionProductMachine._apply_checkers) для
       проверки словаря, возвращённого аспектом.

           checker = ResultStringChecker("txn_id", "ID транзакции", required=True)
           checker.check({"txn_id": "abc"})  # OK
           checker.check({})                  # ValidationFieldError

    MetadataBuilder._collect_checkers(cls) обходит MRO класса, находит методы
    с _checker_meta и собирает их в ClassMetadata.checkers (tuple[CheckerMeta]).

    ActionProductMachine._apply_checkers() создаёт экземпляр чекера из
    CheckerMeta и вызывает checker.check(result_dict).
"""

from abc import abstractmethod
from typing import Any

from action_machine.core.exceptions import ValidationFieldError


class ResultFieldChecker:
    """
    Базовый чекер для полей результата аспекта.

    Поддерживает два режима:
    - Декоратор метода: записывает _checker_meta в функцию.
    - Валидатор: проверяет dict результата через check().

    Наследники реализуют _check_type_and_constraints для проверки
    конкретного типа (строка, число, дата и т.д.).

    Атрибуты:
        field_name : str
            Имя поля в словаре результата аспекта.
        required : bool
            Обязательно ли поле (True — отсутствие или None вызывает ошибку).
        description : str
            Человекочитаемое описание проверки.
    """

    def __init__(self, field_name: str, required: bool = True, description: str = "") -> None:
        """
        Инициализирует чекер.

        Аргументы:
            field_name: имя поля в словаре результата.
            required: обязательно ли поле.
            description: описание проверки для документации и интроспекции.
        """
        self.field_name = field_name
        self.required = required
        self.description = description

    def __call__(self, func_or_result: Any) -> Any:
        """
        Двойной режим работы:

        1. Если получает callable (функцию) — работает как декоратор,
           записывает _checker_meta в функцию и возвращает её.
        2. Если получает dict — работает как валидатор, вызывает check().

        Аргументы:
            func_or_result: функция (при использовании как декоратор)
                           или dict (при использовании как валидатор).

        Возвращает:
            Функцию с прикреплённым _checker_meta (режим декоратора)
            или None (режим валидатора).

        Исключения:
            ValidationFieldError: при ошибке валидации (режим валидатора).
        """
        if callable(func_or_result) and not isinstance(func_or_result, dict):
            return self._decorate(func_or_result)
        # Режим валидатора: func_or_result — это dict результата
        self.check(func_or_result)
        return None

    def _decorate(self, func: Any) -> Any:
        """
        Прикрепляет _checker_meta к функции.

        Вызывается когда чекер используется как декоратор метода-аспекта.
        Порядок с @regular_aspect/@summary_aspect не имеет значения,
        так как оба декоратора записывают разные атрибуты в одну функцию.

        Аргументы:
            func: декорируемая функция (метод-аспект).

        Возвращает:
            Ту же функцию с прикреплённым атрибутом _checker_meta.
        """
        if not hasattr(func, "_checker_meta"):
            func._checker_meta = []

        func._checker_meta.append(self._build_meta())

        return func

    def _build_meta(self) -> dict[str, Any]:
        """
        Строит словарь метаданных чекера для _checker_meta.

        Содержит все параметры, необходимые MetadataBuilder для создания
        CheckerMeta, а ActionProductMachine._apply_checkers — для создания
        экземпляра чекера.

        Возвращает:
            dict с ключами: checker_class, field_name, description, required,
            а также дополнительные параметры конкретного чекера.
        """
        meta: dict[str, Any] = {
            "checker_class": type(self),
            "field_name": self.field_name,
            "description": self.description,
            "required": self.required,
        }
        # Добавляем дополнительные параметры конкретного чекера
        extra = self._get_extra_params()
        meta.update(extra)
        return meta

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Возвращает дополнительные параметры конкретного чекера.

        Переопределяется в наследниках для добавления специфичных параметров
        (min_length, max_length, min_value, max_value, format и т.д.).

        По умолчанию возвращает пустой словарь.

        Возвращает:
            dict с дополнительными параметрами чекера.
        """
        return {}

    def _check_required(self, result: dict[str, Any]) -> Any | None:
        """
        Проверяет наличие и обязательность поля в результате.

        Аргументы:
            result: словарь результата аспекта.

        Возвращает:
            Значение поля, если оно найдено и не None.
            None, если поле необязательно и отсутствует.

        Исключения:
            ValidationFieldError: если обязательное поле отсутствует или None.
        """
        value = result.get(self.field_name)

        if value is None:
            if self.required:
                raise ValidationFieldError(
                    f"Отсутствует обязательный параметр: '{self.field_name}'",
                    field=self.field_name,
                )
            return None

        return value

    def check(self, result: dict[str, Any]) -> None:
        """
        Полная проверка поля в результате аспекта.

        Сначала проверяет наличие и обязательность через _check_required,
        затем делегирует проверку типа и ограничений в _check_type_and_constraints.

        Аргументы:
            result: словарь результата аспекта.

        Исключения:
            ValidationFieldError: при любой ошибке валидации.
        """
        value = self._check_required(result)
        if value is None:
            return
        self._check_type_and_constraints(value)

    @abstractmethod
    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Проверяет тип и ограничения значения.

        Реализуется в каждом конкретном чекере.

        Аргументы:
            value: значение поля (гарантированно не None).

        Исключения:
            ValidationFieldError: если значение не соответствует требованиям.
        """
        pass
