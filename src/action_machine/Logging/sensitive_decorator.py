# src/action_machine/logging/sensitive_decorator.py
"""
Декоратор @sensitive — маскирование чувствительных данных в логах.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Декоратор @sensitive — часть грамматики намерений ActionMachine для защиты
персональных данных. Он помечает свойство (property) класса как содержащее
чувствительные данные. При подстановке значения в шаблон лога
(VariableSubstitutor) система обнаруживает конфигурацию @sensitive и
автоматически маскирует значение по заданным правилам.

═══════════════════════════════════════════════════════════════════════════════
ПРАВИЛА МАСКИРОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

Алгоритм определяет, сколько символов показать:
    visible = min(max_chars, ceil(len(value) * max_percent / 100))

Если visible >= len(value), строка возвращается без изменений.
Иначе: первые `visible` символов + 5 символов замены (char * 5).

Параметры:
    - enabled (bool): включено ли маскирование. По умолчанию True.
    - max_chars (int): максимальное число видимых символов с начала строки.
      По умолчанию 3.
    - char (str): символ замены, одиночный символ. По умолчанию '*'.
    - max_percent (int): максимальный процент видимых символов (0..100).
      По умолчанию 50.

═══════════════════════════════════════════════════════════════════════════════
ОГРАНИЧЕНИЯ (ИНВАРИАНТЫ)
═══════════════════════════════════════════════════════════════════════════════

- Применяется только к свойствам (property) или к функциям, которые станут
  свойствами (перед @property).
- Поддерживается два порядка декораторов:

      @property
      @sensitive(...)
      def email(self): ...

      @sensitive(...)     # тоже работает, но рекомендуется порядок выше
      @property
      def email(self): ...

- Свойство должно быть публичным (имя не начинается с '_').
  Проверка имени выполняется позже (инспектор / инструменты), так как на этапе
  декорирования имя атрибута ещё неизвестно.
- enabled должен быть bool.
- max_chars должен быть неотрицательным int.
- char должен быть строкой длиной 1.
- max_percent должен быть int в диапазоне 0..100.

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА ИНТЕГРАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    @sensitive(True, max_chars=3, char='*', max_percent=50)
        │
        ▼
    property.fget._sensitive_config = {...}
        │
        ▼  SensitiveGateHostInspector.Snapshot + ``get_sensitive_fields()``
        │
        ▼  VariableSubstitutor._get_property_config(obj, attr_name)
    Обнаруживает _sensitive_config → вызывает mask_value(value, config)
        │
        ▼
    Маскированная строка в шаблоне лога

═══════════════════════════════════════════════════════════════════════════════
ПРИМЕР ИСПОЛЬЗОВАНИЯ
═══════════════════════════════════════════════════════════════════════════════

    class UserAccount:
        def __init__(self, email: str, phone: str):
            self._email = email
            self._phone = phone

        @property
        @sensitive(True, max_chars=3, char='*', max_percent=50)
        def email(self) -> str:
            return self._email

        @property
        @sensitive(True, max_chars=4, char='#', max_percent=100)
        def phone(self) -> str:
            return self._phone

    В шаблоне лога:
        "Email: {%context.account.email}"  →  "Email: max*****"
        "Phone: {%context.account.phone}"  →  "Phone: +123#####"

═══════════════════════════════════════════════════════════════════════════════
ОШИБКИ
═══════════════════════════════════════════════════════════════════════════════

    TypeError — enabled не bool; max_chars не int; char не строка;
               max_percent не int; декоратор применён к не-callable/не-property.
    ValueError — max_chars отрицательный; char не один символ;
                max_percent вне диапазона 0..100.
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
