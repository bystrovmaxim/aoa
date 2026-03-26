# src/action_machine/aspects/summary_aspect.py
"""
Декоратор @summary_aspect — объявление завершающего шага действия.

Назначение:
    Помечает метод как summary-аспект — финальный шаг конвейера, который
    формирует результат (Result) действия. В каждом действии допускается
    ровно один summary_aspect. Он выполняется после всех regular_aspect,
    получает накопленный state и возвращает типизированный Result.

Отличия от @regular_aspect:
    - regular_aspect возвращает dict, который мержится в state.
    - summary_aspect возвращает объект Result (наследник BaseResult).
    - regular_aspect может быть несколько, summary_aspect — ровно один.
    - Действие без regular_aspect допустимо (например, PingAction),
      но без summary_aspect — нет.

Ограничения (инварианты):
    - Применяется только к методам (callable), не к классам или свойствам.
    - Метод должен быть асинхронным (async def).
    - Сигнатура метода: ровно 5 параметров (self, params, state, box, connections).
    - Метод должен быть обычным методом экземпляра — не staticmethod, не classmethod.
      Проверка staticmethod/classmethod выполняется позже в __init_subclass__
      хоста, так как на этапе декорирования Python ещё не обернул метод.

Что делает декоратор:
    Прикрепляет к методу атрибут _new_aspect_meta с типом "summary" и описанием.
    Этот атрибут позже считывается в AspectGateHost.__init_subclass__ для
    регистрации summary-аспекта в замороженном шлюзе.

Пример:
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Обработка платежа")
        async def process_payment(self, params, state, box, connections):
            ...
            return {"txn_id": txn_id}

        @summary_aspect("Формирование результата")
        async def build_result(self, params, state, box, connections):
            return OrderResult(
                order_id=f"ORD_{params.user_id}",
                status="created",
                total=params.amount,
            )

    Действие без regular_aspect (только summary):

    @CheckRoles(CheckRoles.NONE)
    class PingAction(BaseAction[BaseParams, BaseResult]):

        @summary_aspect("Pong-ответ")
        async def pong(self, params, state, box, connections):
            result = BaseResult()
            result["message"] = "pong"
            return result

Ошибки:
    TypeError — метод не callable; метод не асинхронный; неверное число параметров.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

# Ожидаемое число параметров: self, params, state, box, connections
_EXPECTED_PARAM_COUNT = 5

# Имена параметров для сообщения об ошибке
_EXPECTED_PARAM_NAMES = "self, params, state, box, connections"


def summary_aspect(description: str = ""):
    """
    Декоратор уровня метода. Помечает метод как summary-аспект (финальный шаг).

    Аргументы:
        description: человекочитаемое описание шага. Используется в логах,
                     плагинах и интроспекции. Например: "Формирование результата",
                     "Сборка ответа".

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
            f"@summary_aspect ожидает строку description, "
            f"получен {type(description).__name__}."
        )

    def decorator(func: Any) -> Any:
        # ── Проверка: цель — вызываемый объект ──
        if not callable(func):
            raise TypeError(
                f"@summary_aspect можно применять только к методам. "
                f"Получен объект типа {type(func).__name__}: {func!r}."
            )

        # ── Проверка: метод асинхронный ──
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(
                f"@summary_aspect(\"{description}\"): метод {func.__name__} "
                f"должен быть асинхронным (async def). "
                f"Синхронные методы не поддерживаются."
            )

        # ── Проверка: число параметров ──
        sig = inspect.signature(func)
        param_count = len(sig.parameters)
        if param_count != _EXPECTED_PARAM_COUNT:
            raise TypeError(
                f"@summary_aspect(\"{description}\"): метод {func.__name__} "
                f"должен принимать {_EXPECTED_PARAM_COUNT} параметров "
                f"({_EXPECTED_PARAM_NAMES}), получено {param_count}."
            )

        # ── Прикрепление метаданных ──
        func._new_aspect_meta = {
            "type": "summary",
            "description": description,
        }

        return func

    return decorator
