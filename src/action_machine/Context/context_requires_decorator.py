# src/action_machine/context/context_requires_decorator.py
"""
Декоратор @context_requires — декларация доступа аспекта к полям контекста.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @context_requires — часть грамматики намерений ActionMachine.
Он объявляет, какие поля контекста (Context) нужны аспекту или обработчику
ошибок. При вызове аспекта машина (ActionProductMachine) создаёт
ContextView с указанными ключами и передаёт его как последний параметр ctx.

Без @context_requires аспект не получает доступа к контексту вообще.
Это реализация принципа минимальных привилегий: аспект видит ровно те
данные, которые объявил как необходимые.

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕНЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор применяется к async-методам, которые являются аспектами
(@regular_aspect, @summary_aspect) или обработчиками ошибок (@on_error).
Записывает frozenset ключей в атрибут func._required_context_keys.

@context_requires располагается ближе к функции (снизу), а декоратор
аспекта — снаружи (сверху). Это гарантирует, что при проверке сигнатуры
в @regular_aspect атрибут _required_context_keys уже записан:

    @regular_aspect("Проверка прав")        # применяется последним
    @result_string("status", required=True)  # чекер
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

Декоратор не валидирует существование ключей в Context, потому что
Context может быть расширен наследниками. Валидация доступа происходит
в рантайме через ContextView.get().

═══════════════════════════════════════════════════════════════════════════════
ВЛИЯНИЕ НА СИГНАТУРУ
═══════════════════════════════════════════════════════════════════════════════

Наличие @context_requires меняет ожидаемое количество параметров метода:

    Аспекты (@regular_aspect, @summary_aspect):
        Без @context_requires → 5 параметров: self, params, state, box, connections
        С @context_requires   → 6 параметров: self, params, state, box, connections, ctx

    Обработчики ошибок (@on_error):
        Без @context_requires → 6 параметров: self, params, state, box, connections, error
        С @context_requires   → 7 параметров: self, params, state, box, connections, error, ctx

Проверку количества параметров выполняют декораторы @regular_aspect,
@summary_aspect и @on_error — они смотрят наличие _required_context_keys
на функции и ожидают соответствующее число.

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ (ИНВАРИАНТЫ)
═══════════════════════════════════════════════════════════════════════════════

- Хотя бы один ключ обязателен (пустой @context_requires бессмыслен).
- Каждый ключ — непустая строка.
- Целевой объект — callable (async-метод).
- Декоратор не проверяет количество параметров и не проверяет,
  является ли метод аспектом — это ответственность @regular_aspect
  и других декораторов.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
        │
        ▼  Декоратор записывает в func._required_context_keys
    frozenset({"user.user_id", "request.trace_id"})
        │
        ▼  @regular_aspect проверяет сигнатуру
    Видит _required_context_keys → ожидает 6 параметров
        │
        ▼  MetadataBuilder → collectors.collect_aspects(cls)
    AspectMeta.context_keys = frozenset({"user.user_id", "request.trace_id"})
        │
        ▼  ActionProductMachine._call_aspect(...)
    context_keys непустой → создаёт ContextView → передаёт как ctx
        │
        ▼  Аспект вызывает ctx.get(Ctx.User.user_id)
    ContextView проверяет allowed_keys → возвращает значение

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.context import Ctx, context_requires

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
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    TypeError — ключ не строка; целевой объект не callable.
    ValueError — ключей не передано (пустой вызов); ключ — пустая строка.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def context_requires(*keys: str) -> Callable[[Any], Any]:
    """
    Декоратор уровня метода. Декларирует поля контекста, необходимые
    аспекту или обработчику ошибок.

    Записывает frozenset ключей в атрибут func._required_context_keys.
    Декораторы @regular_aspect, @summary_aspect и @on_error при проверке
    сигнатуры обнаруживают этот атрибут и ожидают дополнительный
    параметр ctx.

    Аргументы:
        *keys: один или несколько строковых ключей (dot-path).
               Для стандартных полей рекомендуется использовать
               константы Ctx (Ctx.User.user_id, Ctx.Request.trace_id).
               Для кастомных полей — строки ("user.extra.billing_plan").

    Возвращает:
        Декоратор, который записывает _required_context_keys в функцию
        и возвращает функцию без изменений.

    Исключения:
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
        Внутренний декоратор, применяемый к методу.

        Проверяет, что цель — callable. Записывает _required_context_keys
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
