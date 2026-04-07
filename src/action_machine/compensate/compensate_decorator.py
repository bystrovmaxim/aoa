# src/action_machine/compensate/compensate_decorator.py
"""
Модуль: compensate_decorator — декоратор @compensate для объявления компенсаторов.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @compensate(target_aspect_name, description) помечает async-метод
Action-класса как компенсатор для указанного regular-аспекта. При ошибке
в конвейере аспектов компенсаторы уже выполненных аспектов вызываются
в обратном порядке (паттерн Saga).

Декоратор выполняет валидации при определении класса (import-time) и
записывает на метод атрибут _compensate_meta, который позже собирается
коллектором MetadataBuilder.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА
═══════════════════════════════════════════════════════════════════════════════

Привязка компенсатора к аспекту выполняется по СТРОКОВОМУ ИМЕНИ метода-аспекта
(target_aspect_name), а не по ссылке на объект. Это устраняет зависимость
от порядка определения методов в классе. Паттерн аналогичен привязке чекеров
к аспектам по method_name.

Валидация привязки (существует ли аспект с таким именем, является ли он
regular) выполняется НЕ в декораторе, а в MetadataBuilder.build() —
на этапе декорирования класс ещё не полностью определён, и другие методы
могут быть не объявлены.

Декоратор выполняет только те валидации, которые возможны на этапе
определения метода:
    - target_aspect_name — непустая строка
    - description — непустая строка
    - метод — async def
    - имя метода заканчивается на "_compensate"
    - количество параметров: 7 без @context_requires, 8 с @context_requires

═══════════════════════════════════════════════════════════════════════════════
ЗАПИСЫВАЕМЫЙ АТРИБУТ
═══════════════════════════════════════════════════════════════════════════════

Декоратор записывает на функцию атрибут:

    func._compensate_meta = {
        "target_aspect_name": target_aspect_name,
        "description": description,
    }

Этот атрибут читается коллектором collect_compensators() в
metadata/collectors.py, который обходит vars(cls) и создаёт
CompensatorMeta для каждого помеченного метода.

═══════════════════════════════════════════════════════════════════════════════
ВЗАИМОДЕЙСТВИЕ С @context_requires
═══════════════════════════════════════════════════════════════════════════════

Компенсатор может использовать @context_requires. Порядок декораторов:

    @context_requires("user.role", "tenant.id")
    @compensate("process_payment_aspect", "Откат платежа")
    async def rollback_payment_compensate(self, params, state_before,
                                           state_after, box, connections,
                                           error, ctx):
        ...

@context_requires записывает _required_context_keys на функцию.
@compensate проверяет наличие этого атрибута и корректирует ожидаемое
количество параметров: 7 без ctx, 8 с ctx.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.compensate import compensate

    class CreateOrderAction(BaseAction[CreateOrderParams, CreateOrderResult]):

        @regular_aspect("Списание средств")
        async def process_payment_aspect(self, params, state, box, connections):
            ...

        @compensate("process_payment_aspect", "Откат платежа")
        async def rollback_payment_compensate(self, params, state_before,
                                               state_after, box, connections,
                                               error):
            ...
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable


# ─────────────────────────────────────────────────────────────────────────────
# Константы
# ─────────────────────────────────────────────────────────────────────────────

_COMPENSATE_SUFFIX = "_compensate"
"""
Обязательный суффикс имени метода-компенсатора.
Обеспечивает визуальную идентификацию компенсаторов в коде класса
и предотвращает случайное декорирование обычного метода.
"""

_EXPECTED_PARAMS_WITHOUT_CTX = 7
"""
Ожидаемое количество параметров компенсатора без @context_requires:
self, params, state_before, state_after, box, connections, error.
"""

_EXPECTED_PARAMS_WITH_CTX = 8
"""
Ожидаемое количество параметров компенсатора с @context_requires:
self, params, state_before, state_after, box, connections, error, ctx.
"""

_COMPENSATE_META_ATTR = "_compensate_meta"
"""
Имя атрибута, записываемого на метод декоратором @compensate.
Читается коллектором collect_compensators() в metadata/collectors.py.
"""

_CONTEXT_REQUIRES_ATTR = "_required_context_keys"
"""
Имя атрибута, записываемого декоратором @context_requires.
Используется для определения наличия контекстных зависимостей
и корректировки ожидаемого количества параметров.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Декоратор @compensate
# ─────────────────────────────────────────────────────────────────────────────


def compensate(
    target_aspect_name: str,
    description: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Декоратор для объявления метода-компенсатора regular-аспекта.

    Помечает async-метод Action-класса как компенсатор для указанного
    regular-аспекта. При ошибке в конвейере аспектов все компенсаторы
    уже выполненных аспектов вызываются в обратном порядке.

    Аргументы:
        target_aspect_name:
            Строковое имя метода regular-аспекта, к которому привязан
            компенсатор (например, "process_payment_aspect").
            Непустая строка. Валидация существования аспекта и его типа
            выполняется в MetadataBuilder.build(), а не здесь.

        description:
            Человекочитаемое описание действия компенсатора
            (например, "Откат платежа", "Удаление созданной записи").
            Непустая строка. Используется в событиях плагинов,
            логировании и графе зависимостей.

    Возвращает:
        Декоратор, который записывает _compensate_meta на метод
        и возвращает его без изменений.

    Raises:
        TypeError:
            - target_aspect_name не является строкой.
            - description не является строкой.
            - Метод не является корутиной (async def).
            - Неверное количество параметров.
        ValueError:
            - target_aspect_name — пустая строка.
            - description — пустая строка.
            - Имя метода не заканчивается на "_compensate".

    Пример:
        @compensate("process_payment_aspect", "Откат платежа")
        async def rollback_payment_compensate(self, params, state_before,
                                               state_after, box,
                                               connections, error):
            ...
    """

    # ── Валидация аргументов декоратора ────────────────────────────────────

    if not isinstance(target_aspect_name, str):
        raise TypeError(
            f"@compensate: target_aspect_name должен быть строкой, "
            f"получен {type(target_aspect_name).__name__}"
        )

    if not target_aspect_name.strip():
        raise ValueError(
            "@compensate: target_aspect_name не может быть пустой строкой"
        )

    if not isinstance(description, str):
        raise TypeError(
            f"@compensate: description должен быть строкой, "
            f"получен {type(description).__name__}"
        )

    if not description.strip():
        raise ValueError(
            "@compensate: description не может быть пустой строкой"
        )

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Внутренний декоратор: валидирует метод и записывает _compensate_meta.
        """

        method_name = func.__name__

        # ── Валидация суффикса имени ──────────────────────────────────────

        if not method_name.endswith(_COMPENSATE_SUFFIX):
            raise ValueError(
                f"@compensate: имя метода '{method_name}' должно "
                f"заканчиваться на '{_COMPENSATE_SUFFIX}'. "
                f"Это обеспечивает визуальную идентификацию компенсаторов "
                f"в коде класса."
            )

        # ── Валидация async def ───────────────────────────────────────────

        if not asyncio.iscoroutinefunction(func):
            raise TypeError(
                f"@compensate: метод '{method_name}' должен быть "
                f"корутиной (async def). Компенсаторы выполняют "
                f"асинхронные операции отката (HTTP-запросы, запросы к БД)."
            )

        # ── Валидация количества параметров ───────────────────────────────
        #
        # Определяем, использует ли метод @context_requires.
        # @context_requires записывает _required_context_keys ДО вызова
        # @compensate (порядок декораторов: @context_requires снаружи,
        # @compensate внутри).

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

        # ── Запись метаданных на метод ────────────────────────────────────

        setattr(func, _COMPENSATE_META_ATTR, {
            "target_aspect_name": target_aspect_name.strip(),
            "description": description.strip(),
        })

        return func

    return decorator