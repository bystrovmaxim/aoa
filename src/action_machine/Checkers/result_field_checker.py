# src/action_machine/checkers/result_field_checker.py
"""
Базовый абстрактный чекер для полей результата аспекта.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Определяет общий интерфейс для всех чекеров полей. Каждый конкретный
чекер (ResultStringChecker, ResultIntChecker и т.д.) наследует
ResultFieldChecker и реализует метод _check_type_and_constraints.

ResultFieldChecker используется машиной (ActionProductMachine._apply_checkers)
для проверки словаря, возвращённого аспектом. Машина создаёт экземпляр
чекера из CheckerMeta и вызывает checker.check(result_dict).

═══════════════════════════════════════════════════════════════════════════════
ИНВАРИАНТ ИМЕНОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

Каждый класс, наследующий ResultFieldChecker (прямо или косвенно), обязан
иметь суффикс "Checker" в имени. Проверка выполняется в __init_subclass__
при определении класса. Нарушение → NamingSuffixError.

Примеры:
    class ResultStringChecker(ResultFieldChecker):  ← OK
    class ResultIntChecker(ResultFieldChecker):     ← OK
    class MyCustomChecker(ResultFieldChecker):      ← OK
    class StringValidator(ResultFieldChecker):      ← NamingSuffixError

═══════════════════════════════════════════════════════════════════════════════
ИНТЕГРАЦИЯ С ДЕКОРАТОРАМИ
═══════════════════════════════════════════════════════════════════════════════

Функции-декораторы (result_string, result_int и т.д.) записывают метаданные
чекера в атрибут ``_checker_meta`` метода-аспекта. MetadataBuilder собирает
эти метаданные в ClassMetadata.checkers (tuple[CheckerMeta]).

ActionProductMachine при выполнении regular-аспекта:
1. Получает checkers = metadata.get_checkers_for_aspect(aspect_name).
2. Если чекеров нет и аспект вернул непустой dict — ошибка.
3. Если чекеры есть — проверяет, что результат содержит только
   объявленные поля, и применяет каждый чекер через check().

═══════════════════════════════════════════════════════════════════════════════
КОНСТРУКТОР
═══════════════════════════════════════════════════════════════════════════════

Конструктор принимает два параметра:
    - field_name: str — имя поля в словаре результата.
    - required: bool — обязательно ли поле (по умолчанию True).

Конкретные наследники могут добавлять дополнительные параметры
(min_length, max_value и т.д.) через свои конструкторы.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Машина создаёт экземпляр чекера из CheckerMeta и вызывает check():
    checker = ResultStringChecker("txn_id", required=True)
    checker.check({"txn_id": "abc"})  # OK
    checker.check({})                  # ValidationFieldError
"""

from abc import abstractmethod
from typing import Any

from action_machine.core.exceptions import NamingSuffixError, ValidationFieldError

# Суффикс, обязательный для всех классов, наследующих ResultFieldChecker.
_REQUIRED_SUFFIX = "Checker"


class ResultFieldChecker:
    """
    Базовый чекер для полей результата аспекта.

    Используется машиной для валидации словаря, возвращённого аспектом.
    Машина создаёт экземпляр из CheckerMeta и вызывает check(result_dict).

    Наследники реализуют _check_type_and_constraints для проверки
    конкретного типа (строка, число, дата и т.д.).

    Каждый класс-наследник обязан иметь суффикс "Checker" в имени.
    Проверяется при определении класса через __init_subclass__.

    Атрибуты:
        field_name : str
            Имя поля в словаре результата аспекта.
        required : bool
            Обязательно ли поле (True — отсутствие или None вызывает ошибку).
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Вызывается Python при создании любого подкласса ResultFieldChecker.

        Проверяет инвариант именования: имя класса обязано заканчиваться
        на "Checker". Нарушение → NamingSuffixError.

        Аргументы:
            **kwargs: аргументы, передаваемые в type.__init_subclass__.

        Исключения:
            NamingSuffixError: если имя класса не заканчивается на "Checker".
        """
        super().__init_subclass__(**kwargs)

        if not cls.__name__.endswith(_REQUIRED_SUFFIX):
            raise NamingSuffixError(
                f"Класс '{cls.__name__}' наследует ResultFieldChecker, "
                f"но не имеет суффикса '{_REQUIRED_SUFFIX}'. "
                f"Переименуйте в '{cls.__name__}{_REQUIRED_SUFFIX}'."
            )

    def __init__(self, field_name: str, required: bool = True) -> None:
        """
        Инициализирует чекер.

        Аргументы:
            field_name: имя поля в словаре результата.
            required: обязательно ли поле. По умолчанию True.
        """
        self.field_name = field_name
        self.required = required

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
