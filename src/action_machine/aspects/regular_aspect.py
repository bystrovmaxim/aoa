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
ПАРАМЕТРЫ
═══════════════════════════════════════════════════════════════════════════════

    description : str
        Обязательное человекочитаемое описание шага. Непустая строка.
        Используется в логах, плагинах, интроспекции и графе координатора.
        Примеры: "Валидация суммы", "Обработка платежа".

═══════════════════════════════════════════════════════════════════════════════
ПЕРЕМЕННАЯ СИГНАТУРА
═══════════════════════════════════════════════════════════════════════════════

Количество параметров зависит от наличия декоратора @context_requires
на методе. @context_requires применяется ближе к функции (снизу),
поэтому при проверке сигнатуры в @regular_aspect атрибут
_required_context_keys уже записан.

    Без @context_requires:
        5 параметров: self, params, state, box, connections

    С @context_requires:
        6 параметров: self, params, state, box, connections, ctx

Примеры:

    # Без контекста — 5 параметров:
    @regular_aspect("Расчёт суммы")
    async def calculate_aspect(self, params, state, box, connections):
        return {"total": params.amount * 1.2}

    # С контекстом — 6 параметров:
    @regular_aspect("Проверка прав")
    @context_requires(Ctx.User.user_id, Ctx.User.roles)
    async def check_permissions_aspect(self, params, state, box, connections, ctx):
        user_id = ctx.get(Ctx.User.user_id)
        return {}

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ (ИНВАРИАНТЫ)
═══════════════════════════════════════════════════════════════════════════════

- Применяется только к методам (callable), не к классам или свойствам.
- Метод должен быть асинхронным (async def).
- Сигнатура метода: 5 параметров без @context_requires,
  6 параметров с @context_requires.
- description — обязательная непустая строка.
- Имя метода обязано заканчиваться на "_aspect" (проверяется NamingSuffixError).

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @regular_aspect("Валидация суммы")
        │
        ▼  Декоратор записывает в method._new_aspect_meta
    {"type": "regular", "description": "Валидация суммы"}
        │
        ▼  MetadataBuilder._collect_aspects(cls)
    AspectMeta("validate_aspect", "regular", ..., context_keys=frozenset(...))
        │
        ▼  ActionProductMachine._execute_regular_aspects(...)
    Последовательно вызывает каждый regular-аспект, мержит результат в state.
    Если context_keys непустой — создаёт ContextView, передаёт как ctx.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Валидация суммы")
        async def validate_amount_aspect(self, params, state, box, connections):
            if params.amount <= 0:
                raise ValueError("Сумма должна быть положительной")
            return {}

        @regular_aspect("Обработка платежа")
        @result_string("txn_id", required=True)
        async def process_payment_aspect(self, params, state, box, connections):
            payment = box.resolve(PaymentService)
            txn_id = await payment.charge(params.amount, params.currency)
            return {"txn_id": txn_id}

        @regular_aspect("Аудит")
        @context_requires(Ctx.User.user_id, Ctx.Request.client_ip)
        async def audit_aspect(self, params, state, box, connections, ctx):
            user_id = ctx.get(Ctx.User.user_id)
            return {}

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    TypeError — метод не callable; метод не асинхронный; неверное число
               параметров; description не строка.
    ValueError — description пустая строка или строка из пробелов.
    NamingSuffixError — имя метода не заканчивается на "_aspect".
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
_REQUIRED_SUFFIX = "_aspect"


def regular_aspect(description: str) -> Callable[[Any], Any]:
    """
    Декоратор уровня метода. Помечает метод как регулярный аспект конвейера.

    Записывает в метод атрибут _new_aspect_meta с типом "regular" и описанием.
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
            - Имя метода не заканчивается на "_aspect".
    """
    # ── Валидация description ──
    if not isinstance(description, str):
        raise TypeError(
            f"@regular_aspect ожидает строку description, "
            f"получен {type(description).__name__}."
        )

    if not description.strip():
        raise ValueError(
            "@regular_aspect: description не может быть пустой строкой. "
            "Укажите описание шага конвейера."
        )

    def decorator(func: Any) -> Any:
        """
        Внутренний декоратор, применяемый к методу.

        Проверяет:
        1. func — callable.
        2. func — async def.
        3. Число параметров корректно (5 без @context_requires, 6 с ним).
        4. Имя метода заканчивается на "_aspect".

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

        # ── Проверка: число параметров (с учётом @context_requires) ──
        has_context = hasattr(func, "_required_context_keys")
        expected_count = _CTX_PARAM_COUNT if has_context else _BASE_PARAM_COUNT
        expected_names = _CTX_PARAM_NAMES if has_context else _BASE_PARAM_NAMES

        sig = inspect.signature(func)
        param_count = len(sig.parameters)
        if param_count != expected_count:
            raise TypeError(
                f"@regular_aspect(\"{description}\"): метод {func.__name__} "
                f"должен принимать {expected_count} параметров "
                f"({expected_names}), получено {param_count}."
            )

        # ── Проверка: суффикс имени метода ──
        if not func.__name__.endswith(_REQUIRED_SUFFIX):
            raise NamingSuffixError(
                f"@regular_aspect(\"{description}\"): метод '{func.__name__}' "
                f"должен заканчиваться на '{_REQUIRED_SUFFIX}'. "
                f"Переименуйте в '{func.__name__}{_REQUIRED_SUFFIX}' "
                f"или аналогичное имя с суффиксом '{_REQUIRED_SUFFIX}'."
            )

        # ── Прикрепление метаданных ──
        func._new_aspect_meta = {
            "type": "regular",
            "description": description,
        }

        return func

    return decorator
