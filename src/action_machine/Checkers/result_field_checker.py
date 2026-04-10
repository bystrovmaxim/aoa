# src/action_machine/checkers/result_field_checker.py
"""
Базовый абстрактный checker для полей результата аспекта.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Определяет общий интерфейс для всех checkerов полей. Каждый конкретный
checker (ResultStringChecker, ResultIntChecker и т.д.) наследует
ResultFieldChecker и реализует method _check_type_and_constraints.

ResultFieldChecker используется машиной (ActionProductMachine._apply_checkers)
для проверки словаря, возвращённого аспектом. Машина создаёт экземпляр
checkerа из snapshot-метаданных checkerа и вызывает checker.check(result_dict).

═══════════════════════════════════════════════════════════════════════════════
INVARIANT ИМЕНОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

Каждый класс, наследующий ResultFieldChecker (прямо или косвенно), обязан
иметь суффикс "Checker" в имени. Check выполняется в __init_subclass__
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
checkerа в атрибут ``_checker_meta`` methodа-аспекта. MetadataBuilder собирает
эти метаданные в checker snapshot (GateCoordinator.get_checkers).

ActionProductMachine при выполнении regular-аспекта:
1. Получает checkers = coordinator.get_checkers_for_aspect(cls, aspect_name).
2. Если checkerов нет и аспект вернул непустой dict — ошибка.
3. Если checkerы есть — проверяет, что результат содержит только
   объявленные поля, и применяет каждый checker через check().

═══════════════════════════════════════════════════════════════════════════════
КОНСТРУКТОР
═══════════════════════════════════════════════════════════════════════════════

Конструктор принимает два параметра:
    - field_name: str — имя поля в словаре результата.
    - required: bool — required ли поле (по умолчанию True).

Конкретные наследники могут добавлять дополнительные параметры
(min_length, max_value и т.д.) через свои конструкторы.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    # Машина создаёт экземпляр checkerа из snapshot-метаданных и вызывает check():
    checker = ResultStringChecker("txn_id", required=True)
    checker.check({"txn_id": "abc"})  # OK
    checker.check({})                  # ValidationFieldError


AI-CORE-BEGIN
ROLE: module result_field_checker
CONTRACT: Keep runtime behavior unchanged; decorators/inspectors expose metadata consumed by coordinator/machine.
INVARIANTS: Validate declarations early and provide deterministic metadata shape.
FLOW: declarations -> inspector snapshot -> coordinator cache -> runtime usage.
AI-CORE-END
"""

from abc import abstractmethod
from typing import Any

from action_machine.core.exceptions import NamingSuffixError, ValidationFieldError

# Суффикс, обязательный для всех классов, наследующих ResultFieldChecker.
_REQUIRED_SUFFIX = "Checker"


class ResultFieldChecker:
    """
    Базовый checker для полей результата аспекта.

    Используется машиной для валидации словаря, возвращённого аспектом.
    Машина создаёт экземпляр из snapshot-метаданных и вызывает check(result_dict).

    Наследники реализуют _check_type_and_constraints для проверки
    конкретного типа (строка, число, дата и т.д.).

    Каждый класс-наследник обязан иметь суффикс "Checker" в имени.
    Checksся при определении класса через __init_subclass__.

    Атрибуты:
        field_name : str
            Имя поля в словаре результата аспекта.
        required : bool
            Обязательно ли поле (True — отсутствие или None вызывает ошибку).
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Вызывается Python при создании любого подкласса ResultFieldChecker.

        Checks инвариант именования: имя класса обязано заканчиваться
        на "Checker". Нарушение → NamingSuffixError.

        Args:
            **kwargs: аргументы, передаваемые в type.__init_subclass__.

        Raises:
            NamingSuffixError: если имя класса не заканчивается на "Checker".
        """
        super().__init_subclass__(**kwargs)

        if not cls.__name__.endswith(_REQUIRED_SUFFIX):
            raise NamingSuffixError(
                f"Class '{cls.__name__}' наследует ResultFieldChecker, "
                f"но не имеет суффикса '{_REQUIRED_SUFFIX}'. "
                f"Rename в '{cls.__name__}{_REQUIRED_SUFFIX}'."
            )

    def __init__(self, field_name: str, required: bool = True) -> None:
        """
        Инициализирует checker.

        Args:
            field_name: имя поля в словаре результата.
            required: required ли поле. По умолчанию True.
        """
        self.field_name = field_name
        self.required = required

    def _get_extra_params(self) -> dict[str, Any]:
        """
        Returns дополнительные параметры конкретного checkerа.

        Переопределяется в наследниках для добавления специфичных parameters
        (min_length, max_length, min_value, max_value, format и т.д.).

        По умолчанию возвращает пустой словарь.

        Returns:
            dict с дополнительными параметрами checkerа.
        """
        return {}

    def _check_required(self, result: dict[str, Any]) -> Any | None:
        """
        Checks наличие и requiredсть поля в результате.

        Args:
            result: словарь результата аспекта.

        Returns:
            Значение поля, если оно найдено и не None.
            None, если поле неrequired и отсутствует.

        Raises:
            ValidationFieldError: если requiredе поле отсутствует или None.
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

        Сначала проверяет наличие и requiredсть через _check_required,
        затем делегирует проверку типа и ограничений в _check_type_and_constraints.

        Args:
            result: словарь результата аспекта.

        Raises:
            ValidationFieldError: при любой ошибке валидации.
        """
        value = self._check_required(result)
        if value is None:
            return
        self._check_type_and_constraints(value)

    @abstractmethod
    def _check_type_and_constraints(self, value: Any) -> None:
        """
        Checks тип и ограничения значения.

        Реализуется в каждом конкретном checkerе.

        Args:
            value: значение поля (гарантированно не None).

        Raises:
            ValidationFieldError: если значение не соответствует требованиям.
        """
        pass
