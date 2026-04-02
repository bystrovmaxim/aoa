# src/action_machine/aspects/regular_aspect.py
"""
Декоратор @regular_aspect — объявление шага конвейера бизнес-логики.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Помечает метод действия как регулярный аспект — один шаг в линейном
конвейере обработки. Машина (ActionProductMachine) выполняет регулярные
аспекты последовательно, в порядке их объявления в классе. Каждый аспект
получает params, state, box и connections, возвращает dict с новыми полями,
которые добавляются в state для следующего аспекта.

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ (ИНВАРИАНТЫ)
═══════════════════════════════════════════════════════════════════════════════

- Применяется только к методам (callable), не к классам или свойствам.
- Метод должен быть асинхронным (async def).
- Сигнатура метода: ровно 5 параметров (self, params, state, box, connections).

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Валидация суммы")
        │
        ▼  Декоратор записывает в method._new_aspect_meta
    {"type": "regular", "description": "Валидация суммы"}
        │
        ▼  MetadataBuilder._collect_aspects(cls)
    ClassMetadata.aspects = (AspectMeta("validate_amount", "regular", ...), ...)
        │
        ▼  ActionProductMachine._execute_regular_aspects(...)
    Последовательно вызывает каждый regular-аспект, мержит результат в state

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Валидация суммы")
        async def validate_amount(self, params, state, box, connections):
            if params.amount <= 0:
                raise ValueError("Сумма должна быть положительной")
            return {}

        @regular_aspect("Обработка платежа")
        @result_string("txn_id", required=True)
        async def process_payment(self, params, state, box, connections):
            payment = box.resolve(PaymentService)
            txn_id = await payment.charge(params.amount, params.currency)
            return {"txn_id": txn_id}

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    TypeError — метод не callable; метод не асинхронный; неверное число параметров;
               description не строка.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

# Ожидаемое число параметров для regular_aspect: self, params, state, box, connections
_EXPECTED_PARAM_COUNT = 5

# Имена параметров для сообщения об ошибке
_EXPECTED_PARAM_NAMES = "self, params, state, box, connections"


def regular_aspect(description: str = "") -> Callable[[Any], Any]:
    """
    Декоратор уровня метода. Помечает метод как регулярный аспект конвейера.

    Записывает в метод атрибут _new_aspect_meta с типом "regular" и описанием.
    MetadataBuilder._collect_aspects(cls) позже обнаруживает этот атрибут
    и включает метод в ClassMetadata.aspects.

    Аргументы:
        description: человекочитаемое описание шага. Используется в логах,
                     плагинах и интроспекции. Например: "Валидация суммы",
                     "Обработка платежа". По умолчанию пустая строка.

    Возвращает:
        Декоратор, который прикрепляет _new_aspect_meta к методу
        и возвращает метод без изменений.

    Исключения:
        TypeError:
            - description не является строкой.
            - Декорируемый объект не callable.
            - Метод не асинхронный (не async def).
            - Неверное число параметров (ожидается 5).
    """
    if not isinstance(description, str):
        raise TypeError(
            f"@regular_aspect ожидает строку description, "
            f"получен {type(description).__name__}."
        )

    def decorator(func: Any) -> Any:
        """
        Внутренний декоратор, применяемый к методу.

        Проверяет:
        1. func — callable.
        2. func — async def.
        3. Число параметров == 5 (self, params, state, box, connections).

        Затем записывает _new_aspect_meta в func.
        """
        # ── Проверка: цель — вызываемый объект ──
        if not callable(func):
            raise TypeError(
                f"@regular_aspect можно применять только к методам. "
                f"Получен объект типа {type(func).__name__}: {func!r}."
            )

        # ── Проверка: метод асинхронный ──
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(
                f"@regular_aspect(\"{description}\"): метод {func.__name__} "
                f"должен быть асинхронным (async def). "
                f"Синхронные методы не поддерживаются."
            )

        # ── Проверка: число параметров ──
        sig = inspect.signature(func)
        param_count = len(sig.parameters)
        if param_count != _EXPECTED_PARAM_COUNT:
            raise TypeError(
                f"@regular_aspect(\"{description}\"): метод {func.__name__} "
                f"должен принимать {_EXPECTED_PARAM_COUNT} параметров "
                f"({_EXPECTED_PARAM_NAMES}), получено {param_count}."
            )

        # ── Прикрепление метаданных ──
        func._new_aspect_meta = {
            "type": "regular",
            "description": description,
        }

        return func

    return decorator
