# src/action_machine/logging/sensitive_decorator.py
"""
``@sensitive`` — mark properties whose log output should be masked.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Intent-grammar hook for PII: attach masking config to a property getter.
``VariableSubstitutor`` reads ``_sensitive_config`` during ``{%...}`` resolution
and applies ``mask_value``.

═══════════════════════════════════════════════════════════════════════════════
MASKING RULE
═══════════════════════════════════════════════════════════════════════════════

::

    visible = min(max_chars, ceil(len(value) * max_percent / 100))

If ``visible >= len(value)``, return unchanged. Else: first ``visible``
characters plus five repeats of ``char``.

Parameters: ``enabled`` (default True), ``max_chars`` (default 3), ``char``
(default ``'*'``), ``max_percent`` (default 50, range 0–100).

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Target is a ``property`` or a callable that will be wrapped by ``@property``.
- Supported stacks: ``@property`` above ``@sensitive`` (preferred), or the
  reverse order.
- Public property names should not start with ``_`` (enforced elsewhere).
- Parameter types/ranges validated at decoration time.

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

``@sensitive`` → ``fget._sensitive_config`` → inspector snapshot /
``get_sensitive_fields`` → ``VariableSubstitutor._get_property_config`` →
``mask_value`` → masked string in template output.

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

::

    class UserAccount:
        @property
        @sensitive(True, max_chars=3, char="*", max_percent=50)
        def email(self) -> str:
            return self._email

    Template ``Email: {%context.account.email}`` → ``Email: max*****``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS
═══════════════════════════════════════════════════════════════════════════════

``TypeError`` / ``ValueError`` from parameter validation or wrong decorator
target (see runtime messages).

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Property decorator storing masking config for log substitution.
CONTRACT: @sensitive(enabled, max_chars, char, max_percent) on getters.
INVARIANTS: config on fget; consumed only by VariableSubstitutor + inspectors.
FLOW: decorate → _sensitive_config → resolve path → mask_value.
FAILURES: validation at decorate time; masking never suppress errors silently.
EXTENSION POINTS: mask_value rules live in masking module.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# ═════════════════════════════════════════════════════════════════════════════
# Валидация параметров (вынесена для снижения цикломатической сложности)
# ═════════════════════════════════════════════════════════════════════════════


def _validate_sensitive_params(
    enabled: bool,
    max_chars: int,
    char: str,
    max_percent: int,
) -> None:
    """
    Проверяет корректность параметров декоратора @sensitive.

    Вызывается один раз при создании декоратора (до применения к цели).
    Выбрасывает TypeError или ValueError при нарушении контракта.

    Аргументы:
        enabled: включено ли маскирование.
        max_chars: максимальное число видимых символов.
        char: символ замены (одиночный).
        max_percent: максимальный процент видимых символов (0..100).

    Исключения:
        TypeError: если тип параметра не соответствует ожидаемому.
        ValueError: если значение параметра вне допустимого диапазона.
    """
    if not isinstance(enabled, bool):
        raise TypeError(
            f"@sensitive: параметр enabled должен быть bool, "
            f"получен {type(enabled).__name__}."
        )

    if not isinstance(max_chars, int):
        raise TypeError(
            f"@sensitive: параметр max_chars должен быть int, "
            f"получен {type(max_chars).__name__}."
        )

    if max_chars < 0:
        raise ValueError(
            f"@sensitive: max_chars не может быть отрицательным, получено {max_chars}."
        )

    if not isinstance(char, str):
        raise TypeError(
            f"@sensitive: параметр char должен быть строкой, "
            f"получен {type(char).__name__}."
        )

    if len(char) != 1:
        raise ValueError(
            f"@sensitive: char должен быть одним символом, "
            f"получено {len(char)} символов: {char!r}."
        )

    if not isinstance(max_percent, int):
        raise TypeError(
            f"@sensitive: параметр max_percent должен быть int, "
            f"получен {type(max_percent).__name__}."
        )

    if not 0 <= max_percent <= 100:
        raise ValueError(
            f"@sensitive: max_percent должен быть в диапазоне 0..100, "
            f"получено {max_percent}."
        )


# ═════════════════════════════════════════════════════════════════════════════
# Основной декоратор
# ═════════════════════════════════════════════════════════════════════════════


def sensitive(
    enabled: bool = True,
    *,
    max_chars: int = 3,
    char: str = "*",
    max_percent: int = 50,
) -> Callable[[Any], Any]:
    """
    Декоратор уровня свойства. Помечает свойство как содержащее чувствительные данные.

    Может применяться к property (в любом порядке с @property) или к callable
    (функции, которая позже станет getter свойства).

    Записывает конфигурацию маскирования в атрибут _sensitive_config целевой
    функции. Инспектор ``sensitive`` строит снимок; ``get_sensitive_fields()``
    отдаёт ``SensitiveFieldMeta``.

    Аргументы:
        enabled: включено ли маскирование. По умолчанию True.
                 Если False, конфигурация записывается, но маскирование
                 не применяется — значение выводится как есть.
        max_chars: максимальное число видимых символов с начала строки.
                   По умолчанию 3.
        char: символ замены. Одиночный символ. По умолчанию '*'.
        max_percent: максимальный процент видимых символов (0..100).
                     По умолчанию 50.

    Возвращает:
        Декоратор, который прикрепляет _sensitive_config к функции или property.

    Исключения:
        TypeError: enabled не bool; max_chars не int; char не str;
                  max_percent не int; цель не callable и не property.
        ValueError: max_chars < 0; len(char) != 1; max_percent не в 0..100.

    Пример:
        @property
        @sensitive(True, max_chars=3, char='*', max_percent=50)
        def email(self) -> str:
            return self._email
    """
    # ── Проверка аргументов (делегирована в отдельную функцию) ──
    _validate_sensitive_params(enabled, max_chars, char, max_percent)

    config = {
        "enabled": enabled,
        "max_chars": max_chars,
        "char": char,
        "max_percent": max_percent,
    }

    def decorator(target: Any) -> Any:
        """
        Внутренний декоратор, применяемый к цели (property или callable).

        Поддерживает два варианта использования:
        1. target — property: извлекает getter (fget), записывает конфиг,
           возвращает новый property с тем же getter/setter/deleter/doc.
        2. target — callable: записывает конфиг напрямую в функцию,
           возвращает её без изменений.
        """
        # ── Вариант 1: target — property (порядок @sensitive над @property) ──
        if isinstance(target, property):
            fget = target.fget
            if fget is None:
                raise TypeError(
                    "@sensitive: получен property без getter. "
                    "Убедитесь, что @sensitive применён к property с getter."
                )
            fget._sensitive_config = config  # type: ignore[attr-defined]
            # Возвращаем новый property с тем же getter, setter, deleter и doc
            return property(fget, target.fset, target.fdel, target.__doc__)

        # ── Вариант 2: target — callable (порядок @property над @sensitive) ──
        if callable(target):
            target._sensitive_config = config
            return target

        # ── Ни то, ни другое ──
        raise TypeError(
            f"@sensitive можно применять только к свойствам (property) или методам. "
            f"Получен объект типа {type(target).__name__}: {target!r}."
        )

    return decorator
