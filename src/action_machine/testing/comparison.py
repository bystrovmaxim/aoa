# src/action_machine/testing/comparison.py
"""
Сравнение результатов выполнения действия на разных машинах.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Когда TestBench прогоняет действие на нескольких машинах (async и sync),
результаты должны совпадать. Модуль предоставляет функцию compare_results,
которая сравнивает два результата и при расхождении выбрасывает
информативное исключение с указанием конкретных полей, где обнаружено
различие.

═══════════════════════════════════════════════════════════════════════════════
АЛГОРИТМ СРАВНЕНИЯ
═══════════════════════════════════════════════════════════════════════════════

1. Если оба результата — pydantic BaseModel:
   - Сравнение через model_dump() → dict == dict.
   - При расхождении: поиск конкретных полей с различающимися значениями.
   - Сообщение: "Результаты машин расходятся: AsyncMachine.order_id='ORD-1'
     vs SyncMachine.order_id='ORD-2'"

2. Если оба результата — не BaseModel:
   - Fallback на оператор ==.
   - При расхождении: сообщение с repr обоих значений.

3. Если типы результатов различаются:
   - Сообщение: "Типы результатов различаются: AsyncMachine вернул
     OrderResult, SyncMachine вернул PingResult"

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    ResultMismatchError — результаты двух машин не совпадают.
    Содержит атрибуты left_name, right_name, differences для
    программного доступа к деталям расхождения.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.testing.comparison import compare_results

    # Совпадающие результаты — ничего не происходит:
    compare_results(result_async, "AsyncMachine", result_sync, "SyncMachine")

    # Расходящиеся результаты — исключение:
    # ResultMismatchError: "Результаты машин расходятся:
    #   AsyncMachine.order_id='ORD-1' vs SyncMachine.order_id='ORD-2'
    #   AsyncMachine.total=1500.0 vs SyncMachine.total=999.0"
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ResultMismatchError(AssertionError):
    """
    Результаты двух машин не совпадают.

    Наследует AssertionError, чтобы pytest отображал ошибку как
    провалившееся утверждение (assertion failure) с полным трейсбеком
    и сообщением.

    Атрибуты:
        left_name : str
            Имя первой машины (например, "AsyncMachine").
        right_name : str
            Имя второй машины (например, "SyncMachine").
        differences : list[tuple[str, Any, Any]]
            Список расхождений: [(field_name, left_value, right_value), ...].
            Пустой список если расхождение обнаружено на уровне типов
            или через fallback ==.
    """

    def __init__(
        self,
        message: str,
        left_name: str,
        right_name: str,
        differences: list[tuple[str, Any, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.left_name = left_name
        self.right_name = right_name
        self.differences = differences or []


def _find_dict_differences(
    left_dict: dict[str, Any],
    right_dict: dict[str, Any],
    left_name: str,
    right_name: str,
) -> list[tuple[str, Any, Any]]:
    """
    Находит конкретные поля, где значения различаются между двумя словарями.

    Проверяет все ключи из обоих словарей. Для каждого ключа сравнивает
    значения. Отсутствие ключа в одном из словарей считается расхождением
    (значение заменяется на маркер "<отсутствует>").

    Аргументы:
        left_dict: словарь первого результата.
        right_dict: словарь второго результата.
        left_name: имя первой машины (для сообщений).
        right_name: имя второй машины (для сообщений).

    Возвращает:
        Список кортежей (field_name, left_value, right_value) для полей
        с различающимися значениями.
    """
    all_keys = sorted(set(left_dict.keys()) | set(right_dict.keys()))
    differences: list[tuple[str, Any, Any]] = []

    _missing = "<отсутствует>"

    for key in all_keys:
        left_val = left_dict.get(key, _missing)
        right_val = right_dict.get(key, _missing)
        if left_val != right_val:
            differences.append((key, left_val, right_val))

    return differences


def _format_differences(
    differences: list[tuple[str, Any, Any]],
    left_name: str,
    right_name: str,
) -> str:
    """
    Форматирует список расхождений в читаемую строку.

    Каждое расхождение на отдельной строке:
        "  AsyncMachine.order_id='ORD-1' vs SyncMachine.order_id='ORD-2'"

    Аргументы:
        differences: список кортежей (field, left_val, right_val).
        left_name: имя первой машины.
        right_name: имя второй машины.

    Возвращает:
        Отформатированная строка с перечислением расхождений.
    """
    lines: list[str] = []
    for field, left_val, right_val in differences:
        lines.append(
            f"  {left_name}.{field}={left_val!r} vs "
            f"{right_name}.{field}={right_val!r}"
        )
    return "\n".join(lines)


def compare_results(
    left: Any,
    left_name: str,
    right: Any,
    right_name: str,
) -> None:
    """
    Сравнивает результаты двух машин и выбрасывает ResultMismatchError
    при расхождении.

    Стратегия сравнения:
    1. Если типы различаются — ошибка с указанием типов.
    2. Если оба — pydantic BaseModel — сравнение через model_dump().
    3. Иначе — fallback на оператор ==.

    Если результаты совпадают — функция завершается без ошибок.

    Аргументы:
        left: результат первой машины.
        left_name: имя первой машины (для сообщений об ошибке).
        right: результат второй машины.
        right_name: имя второй машины (для сообщений об ошибке).

    Исключения:
        ResultMismatchError: если результаты не совпадают.

    Пример:
        compare_results(async_result, "AsyncMachine", sync_result, "SyncMachine")

        # При расхождении:
        # ResultMismatchError: Результаты машин расходятся:
        #   AsyncMachine.order_id='ORD-1' vs SyncMachine.order_id='ORD-2'
    """
    # Проверка совпадения типов
    if type(left) is not type(right):
        raise ResultMismatchError(
            f"Типы результатов различаются: {left_name} вернул "
            f"{type(left).__name__}, {right_name} вернул "
            f"{type(right).__name__}.",
            left_name=left_name,
            right_name=right_name,
        )

    # Сравнение pydantic-моделей через model_dump()
    if isinstance(left, BaseModel) and isinstance(right, BaseModel):
        left_dict = left.model_dump()
        right_dict = right.model_dump()

        if left_dict == right_dict:
            return

        differences = _find_dict_differences(
            left_dict, right_dict, left_name, right_name,
        )
        diff_text = _format_differences(differences, left_name, right_name)

        raise ResultMismatchError(
            f"Результаты машин расходятся:\n{diff_text}",
            left_name=left_name,
            right_name=right_name,
            differences=differences,
        )

    # Fallback: сравнение через ==
    if left == right:
        return

    raise ResultMismatchError(
        f"Результаты машин расходятся: "
        f"{left_name}={left!r} vs {right_name}={right!r}",
        left_name=left_name,
        right_name=right_name,
    )
