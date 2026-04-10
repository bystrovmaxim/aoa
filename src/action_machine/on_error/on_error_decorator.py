# src/action_machine/on_error/on_error_decorator.py
"""
Декоратор @on_error — объявление обработчика ошибок аспектов действия.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @on_error — часть грамматики намерений ActionMachine. Он объявляет,
что метод действия является обработчиком неперехваченных исключений,
возникающих в regular- или summary-аспектах. Когда аспект бросает
исключение, машина (ActionProductMachine) ищет подходящий обработчик
@on_error по типу исключения (isinstance) и вызывает его.

Обработчик может вернуть Result — тогда ошибка считается обработанной,
и Result подменяет результат действия. Если обработчик сам бросает
исключение — оно оборачивается в OnErrorHandlerError.

═══════════════════════════════════════════════════════════════════════════════
ПАРАМЕТРЫ
═══════════════════════════════════════════════════════════════════════════════

    exception_types : type[Exception] | tuple[type[Exception], ...]
        Один тип исключения или кортеж типов, которые перехватывает
        этот обработчик. Каждый элемент должен быть подклассом Exception.

    description : str
        Обязательное текстовое описание обработчика. Непустая строка.
        Используется в логах, интроспекции и графе координатора.

═══════════════════════════════════════════════════════════════════════════════
ПЕРЕМЕННАЯ СИГНАТУРА
═══════════════════════════════════════════════════════════════════════════════

Количество параметров зависит от наличия декоратора @context_requires
на методе. @context_requires применяется ближе к функции (снизу),
поэтому при проверке сигнатуры в @on_error атрибут
_required_context_keys уже записан.

    Без @context_requires:
        6 параметров: self, params, state, box, connections, error

    С @context_requires:
        7 параметров: self, params, state, box, connections, error, ctx

Обработчик имеет собственный @context_requires, независимый от аспекта,
который упал. Если обработчику нужен контекст — он декларирует свои ключи,
и машина создаёт отдельный ContextView.

Примеры:

    # Без контекста — 6 параметров:
    @on_error(ValueError, description="Ошибка валидации")
    async def handle_validation_on_error(self, params, state, box, connections, error):
        return MyResult(status="validation_error")

    # С контекстом — 7 параметров:
    @on_error(ValueError, description="Ошибка валидации с аудитом")
    @context_requires(Ctx.User.user_id)
    async def handle_validation_on_error(self, params, state, box, connections, error, ctx):
        user_id = ctx.get(Ctx.User.user_id)
        return MyResult(status="validation_error", user_id=user_id)

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ (ИНВАРИАНТЫ)
═══════════════════════════════════════════════════════════════════════════════

- Применяется только к методам (callable), не к классам или свойствам.
- Метод должен быть асинхронным (async def).
- Сигнатура: 6 параметров без @context_requires,
  7 параметров с @context_requires.
- Имя метода обязано заканчиваться на "_on_error".
- description — обязательная непустая строка.
- exception_types — один тип Exception или кортеж типов Exception.
- Каждый элемент exception_types — подкласс Exception.
- Обработчики НЕ наследуются от родительского Action.
- Валидация перекрытия типов (нижестоящий не может ловить типы,
  совпадающие или дочерние к вышестоящему) выполняется в MetadataBuilder.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @on_error(ValueError, description="Обработка ошибки валидации")
        │
        ▼  Декоратор записывает в method._on_error_meta
    {"exception_types": (ValueError,), "description": "..."}
        │
        ▼  OnErrorGateHostInspector._collect_error_handlers(cls)
    ErrorHandler(..., context_keys=frozenset(...))
        │
        ▼  on_error_gate_host.validate_error_handlers(cls, error_handlers)
    Проверяет перекрытие типов.
        │
        ▼  ActionProductMachine._handle_aspect_error(...)
    Если context_keys непустой — создаёт ContextView, передаёт как ctx.
    Аспект бросает ValueError → машина ищет обработчик → вызывает → Result.

═══════════════════════════════════════════════════════════════════════════════
ПОРЯДОК ОБРАБОТЧИКОВ И ПЕРЕКРЫТИЕ ТИПОВ
═══════════════════════════════════════════════════════════════════════════════

Обработчики проверяются сверху вниз в порядке объявления в классе.
Первый подходящий (isinstance(error, exception_types)) вызывается.

Допустимо: сначала более специфичный, потом более общий:
    @on_error(ValueError, ...)      ← специфичный
    @on_error(Exception, ...)       ← общий fallback

Недопустимо: сначала общий, потом специфичный:
    @on_error(Exception, ...)       ← общий перехватит всё
    @on_error(ValueError, ...)      ← мёртвый код → TypeError при сборке

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    @meta(description="Создание заказа", domain=OrdersDomain)
    @check_roles(ROLE_NONE)
    class CreateOrderAction(BaseAction[OrderParams, OrderResult]):

        @regular_aspect("Валидация данных")
        async def validate_aspect(self, params, state, box, connections):
            if not params.user_id:
                raise ValueError("user_id обязателен")
            return {"validated_user": params.user_id}

        @summary_aspect("Формирование результата")
        async def build_result_summary(self, params, state, box, connections):
            return OrderResult(order_id="ORD-1", status="created", total=params.amount)

        @on_error(ValueError, description="Ошибка валидации")
        async def handle_validation_on_error(self, params, state, box, connections, error):
            return OrderResult(order_id="ERR", status="validation_error", total=0)

        # С контекстом:
        @on_error((ConnectionError, TimeoutError), description="Сетевая ошибка")
        @context_requires(Ctx.User.user_id, Ctx.Request.trace_id)
        async def handle_network_on_error(self, params, state, box, connections, error, ctx):
            user_id = ctx.get(Ctx.User.user_id)
            trace = ctx.get(Ctx.Request.trace_id)
            return OrderResult(order_id="ERR", status="network_error", total=0)

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    TypeError — метод не callable; не асинхронный; неверное число параметров;
               exception_types не тип и не кортеж типов; элемент не подкласс
               Exception; description не строка.
    ValueError — description пустая строка.
    NamingSuffixError — имя метода не заканчивается на "_on_error".
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from action_machine.core.exceptions import NamingSuffixError

# Количество параметров без @context_requires: self, params, state, box, connections, error
_BASE_PARAM_COUNT = 6

# Количество параметров с @context_requires: self, params, state, box, connections, error, ctx
_CTX_PARAM_COUNT = 7

# Имена параметров для сообщений об ошибках
_BASE_PARAM_NAMES = "self, params, state, box, connections, error"
_CTX_PARAM_NAMES = "self, params, state, box, connections, error, ctx"

# Обязательный суффикс имени метода
_REQUIRED_SUFFIX = "_on_error"


# ═════════════════════════════════════════════════════════════════════════════
# Валидация аргументов декоратора
# ═════════════════════════════════════════════════════════════════════════════


def _normalize_exception_types(
    exception_types: type[Exception] | tuple[type[Exception], ...],
) -> tuple[type[Exception], ...]:
    """
    Нормализует аргумент exception_types в кортеж типов.

    Принимает один тип или кортеж типов. Проверяет, что каждый
    элемент является подклассом Exception.

    Аргументы:
        exception_types: один тип Exception или кортеж типов.

    Возвращает:
        tuple[type[Exception], ...] — нормализованный кортеж.

    Исключения:
        TypeError: если аргумент не тип и не кортеж типов;
                  если элемент не подкласс Exception.
    """
    if isinstance(exception_types, type):
        if not issubclass(exception_types, Exception):
            raise TypeError(
                f"@on_error: тип {exception_types.__name__} не является "
                f"подклассом Exception."
            )
        return (exception_types,)

    if isinstance(exception_types, tuple):
        if len(exception_types) == 0:
            raise TypeError(
                "@on_error: передан пустой кортеж типов исключений. "
                "Укажите хотя бы один тип."
            )
        for i, exc_type in enumerate(exception_types):
            if not isinstance(exc_type, type):
                raise TypeError(
                    f"@on_error: элемент кортежа [{i}] не является типом, "
                    f"получен {type(exc_type).__name__}: {exc_type!r}."
                )
            if not issubclass(exc_type, Exception):
                raise TypeError(
                    f"@on_error: элемент кортежа [{i}] ({exc_type.__name__}) "
                    f"не является подклассом Exception."
                )
        return exception_types

    raise TypeError(
        f"@on_error: первый аргумент должен быть типом Exception "
        f"или кортежем типов Exception, получен "
        f"{type(exception_types).__name__}: {exception_types!r}."
    )


def _exception_types_invariant(
    exception_types: type[Exception] | tuple[type[Exception], ...],
) -> tuple[type[Exception], ...]:
    return _normalize_exception_types(exception_types)


def _validate_description(description: Any) -> None:
    """
    Проверяет, что description — непустая строка.

    Аргументы:
        description: значение параметра description.

    Исключения:
        TypeError: если description не строка.
        ValueError: если description пустая строка или строка из пробелов.
    """
    if not isinstance(description, str):
        raise TypeError(
            f"@on_error: параметр description должен быть строкой, "
            f"получен {type(description).__name__}: {description!r}."
        )
    if not description.strip():
        raise ValueError(
            "@on_error: description не может быть пустой строкой. "
            "Укажите описание обработчика ошибки."
        )


def _description_invariant(description: Any) -> None:
    _validate_description(description)


def _validate_method(func: Any, description: str) -> None:
    """
    Проверяет, что декорируемый объект — асинхронный метод
    с правильной сигнатурой и суффиксом имени.

    Количество параметров проверяется с учётом наличия @context_requires:
    если функция имеет атрибут _required_context_keys — ожидается 7
    параметров (с ctx), иначе 6 (без ctx).

    Аргументы:
        func: декорируемый объект.
        description: описание из декоратора (для сообщений об ошибках).

    Исключения:
        TypeError: если func не callable; не async; неверное число параметров.
        NamingSuffixError: если имя метода не заканчивается на "_on_error".
    """
    # Проверка: цель — вызываемый объект
    if not callable(func):
        raise TypeError(
            f"@on_error можно применять только к методам. "
            f"Получен объект типа {type(func).__name__}: {func!r}."
        )

    # Проверка: метод асинхронный
    if not asyncio.iscoroutinefunction(func):
        raise TypeError(
            f"@on_error(\"{description}\"): метод {func.__name__} "
            f"должен быть асинхронным (async def). "
            f"Синхронные обработчики не поддерживаются."
        )

    # Проверка: число параметров (с учётом @context_requires)
    has_context = hasattr(func, "_required_context_keys")
    expected_count = _CTX_PARAM_COUNT if has_context else _BASE_PARAM_COUNT
    expected_names = _CTX_PARAM_NAMES if has_context else _BASE_PARAM_NAMES

    sig = inspect.signature(func)
    param_count = len(sig.parameters)
    if param_count != expected_count:
        raise TypeError(
            f"@on_error(\"{description}\"): метод {func.__name__} "
            f"должен принимать {expected_count} параметров "
            f"({expected_names}), получено {param_count}."
        )

    # Проверка: суффикс имени метода
    if not func.__name__.endswith(_REQUIRED_SUFFIX):
        raise NamingSuffixError(
            f"@on_error(\"{description}\"): метод '{func.__name__}' "
            f"должен заканчиваться на '{_REQUIRED_SUFFIX}'. "
            f"Переименуйте в '{func.__name__}{_REQUIRED_SUFFIX}' "
            f"или аналогичное имя с суффиксом '{_REQUIRED_SUFFIX}'."
        )


def _method_contract_invariant(func: Any, description: str) -> None:
    _validate_method(func, description)


# ═════════════════════════════════════════════════════════════════════════════
# Основной декоратор
# ═════════════════════════════════════════════════════════════════════════════


def on_error(
    exception_types: type[Exception] | tuple[type[Exception], ...],
    *,
    description: str,
) -> Callable[[Any], Any]:
    """
    Декоратор уровня метода. Объявляет обработчик ошибок аспектов действия.

    Записывает метаданные в атрибут method._on_error_meta. MetadataBuilder
    собирает эти метаданные в snapshot ``error_handler`` (ErrorHandler).

    Количество параметров проверяется с учётом наличия @context_requires:
    если функция имеет атрибут _required_context_keys — ожидается 7
    параметров (с ctx), иначе 6 (без ctx).

    Аргументы:
        exception_types: один тип Exception или кортеж типов, которые
                         перехватывает этот обработчик. Каждый элемент
                         должен быть подклассом Exception.
        description: обязательное текстовое описание обработчика.
                     Непустая строка. Используется в логах и интроспекции.

    Возвращает:
        Декоратор, который прикрепляет _on_error_meta к методу
        и возвращает метод без изменений.

    Исключения:
        TypeError:
            - exception_types не тип и не кортеж типов.
            - Элемент кортежа не подкласс Exception.
            - description не строка.
            - Метод не callable.
            - Метод не асинхронный.
            - Неверное число параметров (6 без @context_requires,
              7 с @context_requires).
        ValueError:
            - description пустая строка.
        NamingSuffixError:
            - Имя метода не заканчивается на "_on_error".
    """
    # Валидация аргументов декоратора (до применения к методу)
    normalized_types = _exception_types_invariant(exception_types)
    _description_invariant(description)

    def decorator(func: Any) -> Any:
        """
        Внутренний декоратор, применяемый к методу.

        Проверяет callable, async, количество параметров, суффикс.
        Затем записывает _on_error_meta в func.
        """
        _method_contract_invariant(func, description)

        func._on_error_meta = {
            "exception_types": normalized_types,
            "description": description,
        }

        return func

    return decorator
