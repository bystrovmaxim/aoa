# src/action_machine/intents/context/context_requires_decorator.py
"""
Decorator @context_requires — декларация доступа аспекта к полям contextа.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Decorator @context_requires — часть грамматики намерений ActionMachine.
Он объявляет, какие поля contextа (Context) нужны аспекту или обработчику
ошибок. При вызове аспекта машина (ActionProductMachine) создаёт
ContextView с указанными ключами и передаёт его как последний параметр ctx.

Без @context_requires аспект не получает доступа к contextу вообще.
Это реализация принципа минимальных привилегий: аспект видит ровно те
данные, которые объявил как необходимые.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕНЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Decorator применяется к async-methodам, которые являются аспектами
(@regular_aspect, @summary_aspect) или обработчиками ошибок (@on_error).
Записывает frozenset ключей в атрибут func._required_context_keys.

@context_requires располагается ближе к функции (снизу), а декоратор
аспекта — снаружи (сверху). Это гарантирует, что при проверке сигнатуры
в @regular_aspect атрибут _required_context_keys уже записан:

    @regular_aspect("Проверка прав")        # применяется последним
    @result_string("status", required=True)  # checker
    @context_requires(Ctx.User.user_id)      # применяется первым
    async def check_aspect(self, params, state, box, connections, ctx):
        ...

═══════════════════════════════════════════════════════════════════════════════
КЛЮЧИ — СТРОКИ DOT-PATH
═══════════════════════════════════════════════════════════════════════════════

Каждый ключ — строка вида "компонент.поле", соответствующая навигации
через Context.resolve(). Для стандартных полей используются константы
из Ctx (с автодополнением IDE), для кастомных — строки напрямую:

    @context_requires(Ctx.User.user_id, "user.extra.billing_plan")

Decorator не валидирует существование ключей в Context, потому что
Context может быть расширен наследниками. Validation доступа происходит
в рантайме через ContextView.get().

═══════════════════════════════════════════════════════════════════════════════
ВЛИЯНИЕ НА СИГНАТУРУ
═══════════════════════════════════════════════════════════════════════════════

Наличие @context_requires меняет ожидаемое количество parameters methodа:

    Аспекты (@regular_aspect, @summary_aspect):
        Без @context_requires → 5 parameters: self, params, state, box, connections
        С @context_requires   → 6 parameters: self, params, state, box, connections, ctx

    Обработчики ошибок (@on_error):
        Без @context_requires → 6 parameters: self, params, state, box, connections, error
        С @context_requires   → 7 parameters: self, params, state, box, connections, error, ctx

Проверку количества parameters выполняют декораторы @regular_aspect,
@summary_aspect и @on_error — они смотрят наличие _required_context_keys
на функции и ожидают соответствующее число.

═══════════════════════════════════════════════════════════════════════════════
LIMITATIONS (INVARIANTS)
═══════════════════════════════════════════════════════════════════════════════

- Хотя бы один ключ обязателен (пустой @context_requires бессмыслен).
- Каждый ключ — непустая строка.
- Целевой объект — callable (async-method).
- Decorator не проверяет количество parameters и не проверяет,
  является ли method аспектом — это ответственность @regular_aspect
  и других декораторов.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
        │
        ▼  Decorator записывает в func._required_context_keys
    frozenset({"user.user_id", "request.trace_id"})
        │
        ▼  @regular_aspect проверяет сигнатуру
    Видит _required_context_keys → ожидает 6 parameters
        │
        ▼  AspectIntentInspector._collect_aspects(cls)
    aspect_snapshot.context_keys = frozenset({"user.user_id", "request.trace_id"})
        │
        ▼  ActionProductMachine._call_aspect(...)
    context_keys непустой → создаёт ContextView → передаёт как ctx
        │
        ▼  Аспект вызывает ctx.get(Ctx.User.user_id)
    ContextView проверяет allowed_keys → возвращает значение

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.intents.context import Ctx, context_requires

    # Стандартные поля через константы:
    @regular_aspect("Проверка прав")
    @context_requires(Ctx.User.user_id, Ctx.User.roles)
    async def check_permissions_aspect(self, params, state, box, connections, ctx):
        user_id = ctx.get(Ctx.User.user_id)
        roles = ctx.get(Ctx.User.roles)
        return {}

    # Смесь констант и строковых путей:
    @regular_aspect("Биллинг")
    @context_requires(Ctx.User.user_id, "user.extra.billing_plan")
    async def billing_aspect(self, params, state, box, connections, ctx):
        plan = ctx.get("user.extra.billing_plan")
        return {"plan": plan}

    # На обработчике ошибок:
    @on_error(ValueError, description="Ошибка валидации")
    @context_requires(Ctx.User.user_id)
    async def handle_on_error(self, params, state, box, connections, error, ctx):
        user_id = ctx.get(Ctx.User.user_id)
        return ErrorResult(user_id=user_id, error=str(error))

═══════════════════════════════════════════════════════════════════════════════
ERRORS
═══════════════════════════════════════════════════════════════════════════════

    TypeError — ключ не строка; целевой объект не callable.
    ValueError — ключей не передано (пустой вызов); ключ — пустая строка.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def context_requires(*keys: str) -> Callable[[Any], Any]:
    """
    Decorator уровня methodа. Декларирует поля contextа, необходимые
    аспекту или обработчику ошибок.

    Записывает frozenset ключей в атрибут func._required_context_keys.
    Decoratorы @regular_aspect, @summary_aspect и @on_error при проверке
    сигнатуры обнаруживают этот атрибут и ожидают дополнительный
    параметр ctx.

    Args:
        *keys: один или несколько строковых ключей (dot-path).
               Для стандартных полей рекомендуется использовать
               константы Ctx (Ctx.User.user_id, Ctx.Request.trace_id).
               Для кастомных полей — строки ("user.extra.billing_plan").

    Returns:
        Decorator, который записывает _required_context_keys в функцию
        и возвращает функцию без изменений.

    Raises:
        ValueError:
            - Ключей не передано (пустой вызов @context_requires()).
            - Ключ — пустая строка или строка из пробелов.
        TypeError:
            - Ключ не является строкой.
            - Целевой объект не является callable.
    """
    # ── Проверка: хотя бы один ключ ──
    if not keys:
        raise ValueError(
            "@context_requires: необходимо указать хотя бы один ключ. "
            "Пример: @context_requires(Ctx.User.user_id)"
        )

    # ── Проверка каждого ключа ──
    for i, key in enumerate(keys):
        if not isinstance(key, str):
            raise TypeError(
                f"@context_requires: ключ [{i}] должен быть строкой, "
                f"получен {type(key).__name__}: {key!r}."
            )
        if not key.strip():
            raise ValueError(
                f"@context_requires: ключ [{i}] не может быть пустой строкой. "
                f"Укажите dot-path, например 'user.user_id'."
            )

    # ── Формирование frozenset ключей ──
    validated_keys: frozenset[str] = frozenset(keys)

    def decorator(func: Any) -> Any:
        """
        Внутренний декоратор, применяемый к methodу.

        Checks, что цель — callable. Записывает _required_context_keys
        и возвращает функцию без изменений.
        """
        if not callable(func):
            raise TypeError(
                f"@context_requires можно применять только к методам. "
                f"Получен объект типа {type(func).__name__}: {func!r}."
            )

        func._required_context_keys = validated_keys
        return func

    return decorator
