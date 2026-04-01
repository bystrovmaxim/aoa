# src/action_machine/testing/state_validator.py
"""
Валидация state по чекерам предшествующих аспектов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

При тестировании отдельного аспекта (run_aspect) или summary-аспекта
(run_summary) тестировщик передаёт state вручную. Этот state должен
содержать все обязательные поля, которые предшествующие аспекты
записали бы при полном прогоне конвейера.

Модуль проверяет корректность переданного state ПЕРЕД выполнением
аспекта, обнаруживая ошибки тестировщика на раннем этапе с информативными
сообщениями.

═══════════════════════════════════════════════════════════════════════════════
АЛГОРИТМ validate_state_for_aspect
═══════════════════════════════════════════════════════════════════════════════

1. Находит целевой аспект по имени в metadata.aspects.
2. Собирает все regular-аспекты, объявленные ДО целевого.
3. Для каждого предшествующего аспекта получает чекеры через
   metadata.get_checkers_for_aspect(aspect_name).
4. Для каждого чекера с required=True проверяет наличие поля в state.
5. Если поле присутствует — создаёт экземпляр чекера и вызывает
   checker.check(state) для проверки типа и constraints.
6. При ошибке: информативное сообщение с указанием аспекта-источника,
   имени поля, типа чекера и причины ошибки.

═══════════════════════════════════════════════════════════════════════════════
АЛГОРИТМ validate_state_for_summary
═══════════════════════════════════════════════════════════════════════════════

1. Собирает ВСЕ regular-аспекты из metadata.aspects.
2. Для каждого regular-аспекта получает чекеры.
3. Проверяет наличие обязательных полей и применяет чекеры.
4. Логика проверки идентична validate_state_for_aspect, но охватывает
   все regular-аспекты, а не только предшествующие.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.testing import validate_state_for_aspect

    # Проверка state перед вторым аспектом:
    validate_state_for_aspect(metadata, "process_payment", state)
    # Если поле 'validated_user' отсутствует:
    # StateValidationError: "Аспект 'process_payment' ожидает поле
    #   'validated_user' (ResultStringChecker, required) от аспекта
    #   'validate', но оно отсутствует в state"

    # Проверка state перед summary:
    validate_state_for_summary(metadata, state)
    # Если поле 'txn_id' имеет неверный тип:
    # StateValidationError: "Summary ожидает поле 'txn_id'
    #   (ResultStringChecker, required) от аспекта 'process_payment':
    #   Параметр 'txn_id' должен быть строкой, получен int"

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    StateValidationError — обязательное поле отсутствует в state;
                           значение поля не проходит проверку чекером;
                           целевой аспект не найден в метаданных.
"""

from __future__ import annotations

from typing import Any

from action_machine.core.class_metadata import CheckerMeta, ClassMetadata


class StateValidationError(Exception):
    """
    Ошибка валидации state перед выполнением аспекта.

    Выбрасывается когда переданный вручную state не содержит
    обязательных полей или значения полей не проходят проверку
    чекерами предшествующих аспектов.

    Атрибуты:
        field : str | None
            Имя поля, вызвавшего ошибку. None если ошибка не привязана
            к конкретному полю (например, аспект не найден).
        source_aspect : str | None
            Имя аспекта, который должен был записать это поле.
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        source_aspect: str | None = None,
    ) -> None:
        super().__init__(message)
        self.field = field
        self.source_aspect = source_aspect


def _find_aspect_index(metadata: ClassMetadata, aspect_name: str) -> int:
    """
    Находит индекс аспекта по имени в metadata.aspects.

    Аргументы:
        metadata: метаданные класса действия.
        aspect_name: имя метода-аспекта.

    Возвращает:
        int — индекс аспекта в metadata.aspects.

    Исключения:
        StateValidationError: если аспект не найден.
    """
    for i, aspect in enumerate(metadata.aspects):
        if aspect.method_name == aspect_name:
            return i

    available = [a.method_name for a in metadata.aspects]
    raise StateValidationError(
        f"Аспект '{aspect_name}' не найден в метаданных. "
        f"Доступные аспекты: {available}."
    )


def _get_preceding_regular_checkers(
    metadata: ClassMetadata,
    up_to_index: int,
) -> list[tuple[str, CheckerMeta]]:
    """
    Собирает чекеры всех regular-аспектов до указанного индекса (не включая).

    Аргументы:
        metadata: метаданные класса действия.
        up_to_index: индекс целевого аспекта (не включается).

    Возвращает:
        Список кортежей (aspect_name, CheckerMeta) для всех regular-аспектов
        с индексом < up_to_index.
    """
    result: list[tuple[str, CheckerMeta]] = []

    for i in range(up_to_index):
        aspect = metadata.aspects[i]
        if aspect.aspect_type != "regular":
            continue
        checkers = metadata.get_checkers_for_aspect(aspect.method_name)
        for checker_meta in checkers:
            result.append((aspect.method_name, checker_meta))

    return result


def _get_all_regular_checkers(
    metadata: ClassMetadata,
) -> list[tuple[str, CheckerMeta]]:
    """
    Собирает чекеры ВСЕХ regular-аспектов действия.

    Аргументы:
        metadata: метаданные класса действия.

    Возвращает:
        Список кортежей (aspect_name, CheckerMeta).
    """
    result: list[tuple[str, CheckerMeta]] = []

    for aspect in metadata.aspects:
        if aspect.aspect_type != "regular":
            continue
        checkers = metadata.get_checkers_for_aspect(aspect.method_name)
        for checker_meta in checkers:
            result.append((aspect.method_name, checker_meta))

    return result


def _validate_checker_against_state(
    checker_meta: CheckerMeta,
    source_aspect: str,
    target_context: str,
    state: dict[str, Any],
) -> None:
    """
    Проверяет одно поле в state по чекеру.

    Если поле обязательное и отсутствует — StateValidationError.
    Если поле присутствует — создаёт экземпляр чекера и вызывает check().
    Ошибка чекера оборачивается в StateValidationError с контекстом.

    Аргументы:
        checker_meta: метаданные чекера.
        source_aspect: имя аспекта, который должен был записать поле.
        target_context: описание контекста ("Аспект 'X'" или "Summary").
        state: словарь state для проверки.

    Исключения:
        StateValidationError: при ошибке валидации.
    """
    field_name = checker_meta.field_name
    checker_class_name = checker_meta.checker_class.__name__
    required_label = "required" if checker_meta.required else "optional"

    # Проверка наличия обязательного поля
    if checker_meta.required and field_name not in state:
        raise StateValidationError(
            f"{target_context} ожидает поле '{field_name}' "
            f"({checker_class_name}, {required_label}) от аспекта "
            f"'{source_aspect}', но оно отсутствует в state.",
            field=field_name,
            source_aspect=source_aspect,
        )

    # Если поле отсутствует и необязательно — пропускаем
    if field_name not in state:
        return

    # Проверка значения через экземпляр чекера
    try:
        checker_instance = checker_meta.checker_class(
            checker_meta.field_name,
            required=checker_meta.required,
            **checker_meta.extra_params,
        )
        checker_instance.check(state)
    except Exception as exc:
        raise StateValidationError(
            f"{target_context} ожидает поле '{field_name}' "
            f"({checker_class_name}, {required_label}) от аспекта "
            f"'{source_aspect}': {exc}",
            field=field_name,
            source_aspect=source_aspect,
        ) from exc


def validate_state_for_aspect(
    metadata: ClassMetadata,
    aspect_name: str,
    state: dict[str, Any],
) -> None:
    """
    Проверяет корректность state перед выполнением конкретного аспекта.

    Находит целевой аспект, собирает чекеры всех предшествующих
    regular-аспектов и проверяет наличие и корректность обязательных
    полей в state.

    Если целевой аспект — первый в конвейере, предшествующих аспектов
    нет, и state не проверяется (любой state допустим).

    Аргументы:
        metadata: метаданные класса действия (из GateCoordinator.get()).
        aspect_name: имя метода целевого аспекта.
        state: словарь state, переданный тестировщиком.

    Исключения:
        StateValidationError: если аспект не найден; обязательное поле
            отсутствует; значение поля не проходит проверку чекером.

    Пример:
        metadata = coordinator.get(CreateOrderAction)
        validate_state_for_aspect(metadata, "process_payment", {"validated_user": "u1"})
    """
    target_index = _find_aspect_index(metadata, aspect_name)
    preceding_checkers = _get_preceding_regular_checkers(metadata, target_index)
    target_context = f"Аспект '{aspect_name}'"

    for source_aspect, checker_meta in preceding_checkers:
        _validate_checker_against_state(
            checker_meta, source_aspect, target_context, state,
        )


def validate_state_for_summary(
    metadata: ClassMetadata,
    state: dict[str, Any],
) -> None:
    """
    Проверяет корректность state перед выполнением summary-аспекта.

    Собирает чекеры ВСЕХ regular-аспектов и проверяет наличие
    и корректность обязательных полей в state.

    Аргументы:
        metadata: метаданные класса действия (из GateCoordinator.get()).
        state: словарь state, переданный тестировщиком.

    Исключения:
        StateValidationError: если обязательное поле отсутствует;
            значение поля не проходит проверку чекером.

    Пример:
        metadata = coordinator.get(CreateOrderAction)
        validate_state_for_summary(metadata, {"validated_user": "u1", "txn_id": "TXN-1"})
    """
    all_checkers = _get_all_regular_checkers(metadata)

    for source_aspect, checker_meta in all_checkers:
        _validate_checker_against_state(
            checker_meta, source_aspect, "Summary", state,
        )
