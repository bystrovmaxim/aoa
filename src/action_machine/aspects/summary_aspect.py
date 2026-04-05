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
ПЕРЕМЕННАЯ СИГНАТУРА
═══════════════════════════════════════════════════════════════════════════════

Количество параметров зависит от наличия декоратора @context_requires
на методе. @context_requires применяется ближе к функции (снизу),
поэтому при проверке сигнатуры в @summary_aspect атрибут
_required_context_keys уже записан.

    Без @context_requires:
        5 параметров: self, params, state, box, connections

    С @context_requires:
        6 параметров: self, params, state, box, connections, ctx

Примеры:

    # Без контекста — 5 параметров:
    @summary_aspect("Формирование результата")
    async def build_result_summary(self, params, state, box, connections):
        return OrderResult(...)

    # С контекстом — 6 параметров:
    @summary_aspect("Формирование результата с аудитом")
    @context_requires(Ctx.User.user_id)
    async def build_result_summary(self, params, state, box, connections, ctx):
        user_id = ctx.get(Ctx.User.user_id)
        return OrderResult(created_by=user_id, ...)

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
- Сигнатура метода: 5 параметров без @context_requires,
  6 параметров с @context_requires.
- description — обязательная непустая строка.
- Имя метода обязано заканчиваться на "_summary" или быть равным "summary"
  (исключение из правила дублирования: "summary_summary" не требуется).

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @summary_aspect("Формирование результата")
        │
        ▼  Декоратор записывает в method._new_aspect_meta
    {"type": "summary", "description": "Формирование результата"}
        │
        ▼  MetadataBuilder._collect_aspects(cls)
    AspectMeta("build_result_summary", "summary", ..., context_keys=frozenset(...))
        │
        ▼  ActionProductMachine._call_aspect(summary_meta, ...)
    Если context_keys непустой — создаёт ContextView, передаёт как ctx.
    Вызывает метод, получает BaseResult.

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

# Количество параметров без @context_requires: self, params, state, box, connections
_BASE_PARAM_COUNT = 5

# Количество параметров с @context_requires: self, params, state, box, connections, ctx
_CTX_PARAM_COUNT = 6

# Имена параметров для сообщений об ошибках
_BASE_PARAM_NAMES = "self, params, state, box, connections"
_CTX_PARAM_NAMES = "self, params, state, box, connections, ctx"

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

    Количество параметров проверяется с учётом наличия @context_requires:
    если функция имеет атрибут _required_context_keys — ожидается 6
    параметров (с ctx), иначе 5 (без ctx).

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
            - Неверное число параметров (5 без @context_requires,
              6 с @context_requires).
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
        3. Число параметров корректно (5 без @context_requires, 6 с ним).
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

        # ── Проверка: число параметров (с учётом @context_requires) ──
        has_context = hasattr(func, "_required_context_keys")
        expected_count = _CTX_PARAM_COUNT if has_context else _BASE_PARAM_COUNT
        expected_names = _CTX_PARAM_NAMES if has_context else _BASE_PARAM_NAMES

        sig = inspect.signature(func)
        param_count = len(sig.parameters)
        if param_count != expected_count:
            raise TypeError(
                f"@summary_aspect(\"{description}\"): метод {func.__name__} "
                f"должен принимать {expected_count} параметров "
                f"({expected_names}), получено {param_count}."
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
