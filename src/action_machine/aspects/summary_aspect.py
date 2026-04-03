# src/action_machine/aspects/summary_aspect.py
"""
Декоратор @summary_aspect — объявление завершающего шага действия.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Помечает метод как summary-аспект — финальный шаг конвейера, который
формирует результат (Result) действия. В каждом действии допускается
ровно один summary_aspect. Он выполняется после всех regular_aspect,
получает накопленный state и возвращает типизированный Result.

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТРЫ
═══════════════════════════════════════════════════════════════════════════════

    description : str
        Обязательное человекочитаемое описание шага. Непустая строка.
        Используется в логах, плагинах, интроспекции и графе координатора.
        Примеры: "Формирование результата", "Сборка ответа".

═══════════════════════════════════════════════════════════════════════════════
ОТЛИЧИЯ ОТ @regular_aspect
═══════════════════════════════════════════════════════════════════════════════

- regular_aspect возвращает dict, который мержится в state.
- summary_aspect возвращает объект Result (наследник BaseResult).
- regular_aspect может быть несколько, summary_aspect — ровно один.
- Действие без regular_aspect допустимо (например, PingAction),
  но без summary_aspect — нет.

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ (ИНВАРИАНТЫ)
═══════════════════════════════════════════════════════════════════════════════

- Применяется только к методам (callable), не к классам или свойствам.
- Метод должен быть асинхронным (async def).
- Сигнатура метода: ровно 5 параметров (self, params, state, box, connections).
- description — обязательная непустая строка.
- Имя метода обязано заканчиваться на "_summary" или быть равным "summary"
  (исключение из правила дублирования: "summary_summary" не требуется).
  Проверяется через NamingSuffixError.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @summary_aspect("Формирование результата")
        │
        ▼  Декоратор записывает в method._new_aspect_meta
    {"type": "summary", "description": "Формирование результата"}
        │
        ▼  MetadataBuilder._collect_aspects(cls)
    ClassMetadata.aspects = (..., AspectMeta("build_result_summary", "summary", ...))
        │
        ▼  ActionProductMachine._call_aspect(summary_meta, ...)
    Вызывает метод, получает BaseResult

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Обработка платежа")
        async def process_payment_aspect(self, params, state, box, connections):
            ...
            return {"txn_id": txn_id}

        @summary_aspect("Формирование результата")
        async def build_result_summary(self, params, state, box, connections):
            return OrderResult(
                order_id=f"ORD_{params.user_id}",
                status="created",
                total=params.amount,
            )

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    TypeError — метод не callable; метод не асинхронный; неверное число
               параметров; description не строка.
    ValueError — description пустая строка или строка из пробелов.
    NamingSuffixError — имя метода не заканчивается на "_summary"
                        и не равно "summary".
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from action_machine.core.exceptions import NamingSuffixError

# Ожидаемое число параметров: self, params, state, box, connections
_EXPECTED_PARAM_COUNT = 5

# Имена параметров для сообщения об ошибке
_EXPECTED_PARAM_NAMES = "self, params, state, box, connections"

# Обязательный суффикс имени метода
_REQUIRED_SUFFIX = "_summary"

# Имя-исключение: метод "summary" допустим без дублирования суффикса
_BARE_NAME = "summary"


def summary_aspect(description: str) -> Callable[[Any], Any]:
    """
    Декоратор уровня метода. Помечает метод как summary-аспект (финальный шаг).

    Записывает в метод атрибут _new_aspect_meta с типом "summary" и описанием.
    MetadataBuilder._collect_aspects(cls) позже обнаруживает этот атрибут
    и включает метод в ClassMetadata.aspects.

    Аргументы:
        description: обязательное человекочитаемое описание шага. Непустая
                     строка. Используется в логах, плагинах и интроспекции.

    Возвращает:
        Декоратор, который прикрепляет _new_aspect_meta к методу
        и возвращает метод без изменений.

    Исключения:
        TypeError:
            - description не является строкой.
            - Декорируемый объект не callable.
            - Метод не асинхронный (не async def).
            - Неверное число параметров (ожидается 5).
        ValueError:
            - description пустая строка или строка из пробелов.
        NamingSuffixError:
            - Имя метода не заканчивается на "_summary" и не равно "summary".
    """
    # ── Валидация description ──
    if not isinstance(description, str):
        raise TypeError(
            f"@summary_aspect ожидает строку description, "
            f"получен {type(description).__name__}."
        )

    if not description.strip():
        raise ValueError(
            "@summary_aspect: description не может быть пустой строкой. "
            "Укажите описание завершающего шага."
        )

    def decorator(func: Any) -> Any:
        """
        Внутренний декоратор, применяемый к методу.

        Проверяет:
        1. func — callable.
        2. func — async def.
        3. Число параметров == 5 (self, params, state, box, connections).
        4. Имя метода заканчивается на "_summary" или равно "summary".

        Затем записывает _new_aspect_meta в func.
        """
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

        # ── Проверка: суффикс имени метода ──
        # Исключение: имя "summary" допустимо без дублирования ("summary_summary" не требуется)
        if func.__name__ != _BARE_NAME and not func.__name__.endswith(_REQUIRED_SUFFIX):
            raise NamingSuffixError(
                f"@summary_aspect(\"{description}\"): метод '{func.__name__}' "
                f"должен заканчиваться на '{_REQUIRED_SUFFIX}'. "
                f"Переименуйте в '{func.__name__}{_REQUIRED_SUFFIX}' "
                f"или аналогичное имя с суффиксом '{_REQUIRED_SUFFIX}'."
            )

        # ── Прикрепление метаданных ──
        func._new_aspect_meta = {
            "type": "summary",
            "description": description,
        }

        return func

    return decorator
