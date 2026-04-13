# src/action_machine/intents/compensate/compensate_decorator.py
"""
Модуль: compensate_decorator — декоратор @compensate для объявления compensatorов.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Декоратор @compensate(target_aspect_name, description) помечает async-method
Action-класса как compensator для указанного regular-аспекта. При ошибке
в конвейере аспектов compensatorы уже выполненных аспектов вызываются
в обратном порядке (паттерн Saga).

Декоратор выполняет валидации при определении класса (import-time) и
записывает на method атрибут _compensate_meta, который позже собирается
коллектором MetadataBuilder.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE
═══════════════════════════════════════════════════════════════════════════════

Привязка compensatorа к аспекту выполняется по СТРОКОВОМУ ИМЕНИ methodа-аспекта
(target_aspect_name), а не по ссылке на объект. Это устраняет зависимость
от порядка определения methodов в классе. Паттерн аналогичен привязке checkerов
к аспектам по method_name.

Validation привязки (существует ли аспект с таким именем, является ли он
regular) выполняется НЕ в декораторе, а в MetadataBuilder.build() —
на этапе декорирования класс ещё не полностью определён, и другие methodы
могут быть не объявлены.

Декоратор выполняет только те валидации, которые возможны на этапе
определения methodа:
    - target_aspect_name — непустая строка
    - description — непустая строка
    - method — async def
    - имя methodа заканчивается на "_compensate"
    - количество parameters: 7 без @context_requires, 8 с @context_requires

═══════════════════════════════════════════════════════════════════════════════
ЗАПИСЫВАЕМЫЙ АТРИБУТ
═══════════════════════════════════════════════════════════════════════════════

Декоратор записывает на функцию атрибут:

    func._compensate_meta = {
        "target_aspect_name": target_aspect_name,
        "description": description,
    }

Этот атрибут читается локальным сборщиком compensatorов
(``CompensateIntentInspector._collect_compensators`` / builder helper),
который обходит ``vars(cls)`` и создаёт snapshot-элементы compensatorов.

═══════════════════════════════════════════════════════════════════════════════
ВЗАИМОДЕЙСТВИЕ С @context_requires
═══════════════════════════════════════════════════════════════════════════════

Компенсатор может использовать @context_requires. Порядок декораторов:

    @context_requires("user.role", "tenant.id")
    @compensate("process_payment_aspect", "Rollback платежа")
    async def rollback_payment_compensate(self, params, state_before,
                                           state_after, box, connections,
                                           error, ctx):
        ...

@context_requires записывает _required_context_keys на функцию.
@compensate проверяет наличие этого атрибута и корректирует ожидаемое
количество parameters: 7 без ctx, 8 с ctx.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.compensate import compensate

    class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):

        @regular_aspect("Charge payment")
        async def process_payment_aspect(self, params, state, box, connections):
            ...

        @compensate("process_payment_aspect", "Rollback платежа")
        async def rollback_payment_compensate(self, params, state_before,
                                               state_after, box, connections,
                                               error):
            ...


AI-CORE-BEGIN
ROLE: module compensate_decorator
CONTRACT: Keep runtime behavior unchanged; decorators/inspectors expose metadata consumed by coordinator/machine.
INVARIANTS: Validate declarations early and provide deterministic metadata shape.
FLOW: declarations -> inspector snapshot -> coordinator cache -> runtime usage.
AI-CORE-END
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Константы
# ─────────────────────────────────────────────────────────────────────────────

_COMPENSATE_SUFFIX = "_compensate"
"""
Обязательный суффикс имени methodа-compensatorа.
Обеспечивает визуальную идентификацию compensatorов в коде класса
и предотвращает случайное декорирование обычного methodа.
"""

_EXPECTED_PARAMS_WITHOUT_CTX = 7
"""
Ожидаемое количество parameters compensatorа без @context_requires:
self, params, state_before, state_after, box, connections, error.
"""

_EXPECTED_PARAMS_WITH_CTX = 8
"""
Ожидаемое количество parameters compensatorа с @context_requires:
self, params, state_before, state_after, box, connections, error, ctx.
"""

_COMPENSATE_META_ATTR = "_compensate_meta"
"""
Имя атрибута, записываемого на method декоратором @compensate.
Читается локальным сборщиком compensatorов в inspector/builder.
"""

_CONTEXT_REQUIRES_ATTR = "_required_context_keys"
"""
Имя атрибута, записываемого декоратором @context_requires.
Используется для определения наличия контекстных зависимостей
и корректировки ожидаемого количества parameters.
"""


def _target_aspect_type_invariant(target_aspect_name: Any) -> None:
    if not isinstance(target_aspect_name, str):
        raise TypeError(
            f"@compensate: target_aspect_name должен быть строкой, "
            f"got {type(target_aspect_name).__name__}"
        )


def _target_aspect_non_empty_invariant(target_aspect_name: str) -> None:
    if not target_aspect_name.strip():
        raise ValueError(
            "@compensate: target_aspect_name не может быть пустой строкой"
        )


def _description_type_invariant(description: Any) -> None:
    if not isinstance(description, str):
        raise TypeError(
            f"@compensate: description должен быть строкой, "
            f"got {type(description).__name__}"
        )


def _description_non_empty_invariant(description: str) -> None:
    if not description.strip():
        raise ValueError(
            "@compensate: description не может быть пустой строкой"
        )


def _method_suffix_invariant(method_name: str) -> None:
    if not method_name.endswith(_COMPENSATE_SUFFIX):
        raise ValueError(
            f"@compensate: имя methodа '{method_name}' должно "
            f"заканчиваться на '{_COMPENSATE_SUFFIX}'. "
            f"Это обеспечивает визуальную идентификацию compensatorов "
            f"в коде класса."
        )


def _method_async_invariant(func: Callable[..., Any], method_name: str) -> None:
    if not asyncio.iscoroutinefunction(func):
        raise TypeError(
            f"@compensate: method '{method_name}' должен быть "
            f"корутиной (async def). Компенсаторы выполняют "
            f"асинхронные операции отката (HTTP-запросы, запросы к БД)."
        )


def _method_params_count_invariant(func: Callable[..., Any], method_name: str) -> None:
    has_context = hasattr(func, _CONTEXT_REQUIRES_ATTR)
    expected_params = (
        _EXPECTED_PARAMS_WITH_CTX if has_context
        else _EXPECTED_PARAMS_WITHOUT_CTX
    )
    sig = inspect.signature(func)
    actual_params = len(sig.parameters)
    if actual_params != expected_params:
        if has_context:
            params_desc = (
                "self, params, state_before, state_after, "
                "box, connections, error, ctx"
            )
        else:
            params_desc = (
                "self, params, state_before, state_after, "
                "box, connections, error"
            )

        raise TypeError(
            f"@compensate: метод '{method_name}' должен иметь "
            f"{expected_params} параметров ({params_desc}), "
            f"но имеет {actual_params}. "
            f"{'Обнаружен @context_requires — добавлен параметр ctx.' if has_context else ''}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Декоратор @compensate
# ─────────────────────────────────────────────────────────────────────────────


def compensate(
    target_aspect_name: str,
    description: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Декоратор для объявления methodа-compensatorа regular-аспекта.

    Помечает async-method Action-класса как compensator для указанного
    regular-аспекта. При ошибке в конвейере аспектов все compensatorы
    уже выполненных аспектов вызываются в обратном порядке.

    Args:
        target_aspect_name:
            Строковое имя methodа regular-аспекта, к которому привязан
            compensator (например, "process_payment_aspect").
            Непустая строка. Validation существования аспекта и его типа
            выполняется в MetadataBuilder.build(), а не здесь.

        description:
            Человекочитаемое описание действия compensatorа
            (например, "Rollback платежа", "Удаление созданной записи").
            Непустая строка. Используется в событиях плагинов,
            логировании и графе зависимостей.

    Returns:
        Декоратор, который записывает _compensate_meta на method
        и возвращает его без изменений.

    Raises:
        TypeError:
            - target_aspect_name не является строкой.
            - description не является строкой.
            - Метод не является корутиной (async def).
            - Неверное количество parameters.
        ValueError:
            - target_aspect_name — пустая строка.
            - description — пустая строка.
            - Имя methodа не заканчивается на "_compensate".

    Пример:
        @compensate("process_payment_aspect", "Rollback платежа")
        async def rollback_payment_compensate(self, params, state_before,
                                               state_after, box,
                                               connections, error):
            ...
    """

    # ── Validation аргументов декоратора ────────────────────────────────────

    _target_aspect_type_invariant(target_aspect_name)
    _target_aspect_non_empty_invariant(target_aspect_name)
    _description_type_invariant(description)
    _description_non_empty_invariant(description)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Внутренний декоратор: валидирует method и записывает _compensate_meta.
        """

        method_name = func.__name__

        # ── Validation суффикса имени ──────────────────────────────────────

        _method_suffix_invariant(method_name)

        # ── Validation async def ───────────────────────────────────────────

        _method_async_invariant(func, method_name)

        # ── Validation количества parameters ───────────────────────────────
        #
        # Определяем, использует ли method @context_requires.
        # @context_requires записывает _required_context_keys ДО вызова
        # @compensate (порядок декораторов: @context_requires снаружи,
        # @compensate внутри).

        _method_params_count_invariant(func, method_name)

        # ── Запись метаданных на method ────────────────────────────────────

        setattr(func, _COMPENSATE_META_ATTR, {
            "target_aspect_name": target_aspect_name.strip(),
            "description": description.strip(),
        })

        return func

    return decorator
