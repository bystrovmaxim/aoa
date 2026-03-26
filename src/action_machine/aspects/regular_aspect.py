# src/action_machine/aspects/regular_aspect.py
"""
Декоратор @regular_aspect — объявление шага конвейера бизнес-логики.

Назначение:
    Помечает метод действия как регулярный аспект — один шаг в линейном
    конвейере обработки. Машина (ActionProductMachine) выполняет регулярные
    аспекты последовательно, в порядке их объявления в классе. Каждый аспект
    получает params, state, box и connections, возвращает dict с новыми полями,
    которые добавляются в state для следующего аспекта.

Ограничения (инварианты):
    - Применяется только к методам (callable), не к классам или свойствам.
    - Метод должен быть асинхронным (async def).
    - Сигнатура метода: ровно 5 параметров (self, params, state, box, connections).
    - Метод должен быть обычным методом экземпляра — не staticmethod, не classmethod.
      Проверка staticmethod/classmethod выполняется позже в __init_subclass__
      хоста, так как на этапе декорирования Python ещё не обернул метод.

Что делает декоратор:
    Прикрепляет к методу атрибут _new_aspect_meta с типом "regular" и описанием.
    Этот атрибут позже считывается в AspectGateHost.__init_subclass__ для
    построения замороженного списка аспектов.

Пример:
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Валидация суммы")
        async def validate_amount(self, params, state, box, connections):
            if params.amount <= 0:
                raise ValueError("Сумма должна быть положительной")
            return {}

        @regular_aspect("Обработка платежа")
        @ResultStringChecker("txn_id", "Идентификатор транзакции", required=True)
        async def process_payment(self, params, state, box, connections):
            payment = box.resolve(PaymentService)
            txn_id = await payment.charge(params.amount, params.currency)
            return {"txn_id": txn_id}

Ошибки:
    TypeError — метод не callable; метод не асинхронный; неверное число параметров.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

# Ожидаемое число параметров для regular_aspect: self, params, state, box, connections
_EXPECTED_PARAM_COUNT = 5

# Имена параметров для сообщения об ошибке
_EXPECTED_PARAM_NAMES = "self, params, state, box, connections"


def regular_aspect(description: str = ""):
    """
    Декоратор уровня метода. Помечает метод как регулярный аспект конвейера.

    Аргументы:
        description: человекочитаемое описание шага. Используется в логах,
                     плагинах и интроспекции. Например: "Валидация суммы",
                     "Обработка платежа".

    Возвращает:
        Декоратор, который прикрепляет _new_aspect_meta к методу.

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
