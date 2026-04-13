# src/action_machine/intents/logging/expression_evaluator.py
"""
Вычислитель выражений для шаблонов логирования ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Использует библиотеку simpleeval для безопасного вычисления выражений
внутри конструкции {iif(condition; true_value; false_value)}.

simpleeval не поддерживает import, exec, eval, __builtins__ и любой доступ
к файловой системе или сети. Это гарантирует, что шаблон логгера не может
выполнить произвольный код.

═══════════════════════════════════════════════════════════════════════════════
ВОЗМОЖНОСТИ ВЫЧИСЛИТЕЛЯ
═══════════════════════════════════════════════════════════════════════════════

- Операторы сравнения: ==, !=, >, <, >=, <=
- Логические операторы: and, or, not
- Арифметика: +, -, *, /
- Встроенные функции: len, upper, lower, format_number, str, int, float, abs
- Цветовые функции: red, green, yellow, blue, magenta, cyan, white, grey
- Функция debug(obj): возвращает форматированную строку с публичными
  полями/свойствами объекта (интроспекция для шаблонов логирования).
  Показывает только непосредственные поля объекта (max_depth=1),
  чтобы не засорять логи. Для глубокой интроспекции вызывайте debug
  на вложенном атрибуте напрямую.
- Функция exists(name): возвращает True если переменная с указанным
  именем существует в текущем контексте вычисления, False иначе.

Цветовые функции возвращают строку, обёрнутую в маркер вида
`__COLOR(red)text__COLOR_END__`, который позже заменяется на реальные
ANSI-коды в VariableSubstitutor._apply_color_filters().

═══════════════════════════════════════════════════════════════════════════════
ИНТРОСПЕКЦИЯ ОБЪЕКТОВ (debug)
═══════════════════════════════════════════════════════════════════════════════

Функция debug() и фильтр |debug используют _inspect_object() для
форматированного вывода публичных полей объекта.

Ключевые особенности:
- max_depth=1 по умолчанию: вложенные объекты не раскрываются,
  показываются как repr(value).
- Циклические ссылки обнаруживаются через множество visited (id объектов)
  и помечаются как <cycle detected>. Проверка циклов выполняется
  ДО проверки max_depth, чтобы обнаружить цикл даже на первом уровне.
- Свойства с @sensitive маскируются по конфигурации декоратора.
- Pydantic class-level атрибуты (model_fields, model_config и т.д.)
  фильтруются через множество _PYDANTIC_CLASS_ATTRS для совместимости
  с Pydantic V2.11+ (избежание DeprecationWarning).

═══════════════════════════════════════════════════════════════════════════════
ОГОВОРКИ (КОНФИДЕНЦИАЛЬНОСТЬ И ОБЪЁМ ЛОГОВ)
═══════════════════════════════════════════════════════════════════════════════

- Секретные поля нужно помечать ``@sensitive``; без декоратора маскирование
  к ним не применяется.
- ``debug()`` и фильтр ``|debug`` печатают поля верхнего уровня переданного
  объекта. Если в шаблон попадает «тяжёлый» объект из контекста, в лог может
  уйти много данных или громоздкие ``repr`` — ограничивайте, что передаёте
  в шаблон, и по-прежнему используйте ``@sensitive`` на чувствительных свойствах.

═══════════════════════════════════════════════════════════════════════════════
ПОЛИТИКА ОШИБОК
═══════════════════════════════════════════════════════════════════════════════

Ошибки не подавляются. Если выражение невалидно — LogTemplateError.
Ошибка в шаблоне лога — баг разработчика, обнаруживаемый немедленно
при первом запуске.

Разбор аргументов iif выполняется классом _IifArgSplitter,
корректно обрабатывающим вложенные скобки и строковые литералы.

Ограничение grammar-by-design: вложенные шаблонные конструкции
``{iif(...{iif(...)}...)}`` не поддерживаются в process_template().
Поддерживается только один уровень шаблонного ``{iif(...)}``; если
нужна вложенная логика, выносите её в отдельные поля/выражения.
"""

import re
from typing import Any

from pydantic import BaseModel
from simpleeval import EvalWithCompoundTypes, NameNotDefined

from action_machine.intents.logging.masking import mask_value
from action_machine.model.exceptions import LogTemplateError

# Регулярное выражение для поиска {iif(...)} в шаблоне.
# Важно: паттерн намеренно НЕ поддерживает вложенные template-level iif.
_IIF_PATTERN: re.Pattern[str] = re.compile(r"\{iif\((.+?)\)\}")

# Атрибуты уровня класса pydantic BaseModel, к которым нельзя обращаться
# через экземпляр (DeprecationWarning в Pydantic V2.11+).
_PYDANTIC_CLASS_ATTRS: frozenset[str] = frozenset({
    "model_fields",
    "model_computed_fields",
    "model_config",
    "model_extra",
    "model_fields_set",
    "model_json_schema",
    "model_parametrized_name",
    "model_post_init",
    "model_rebuild",
    "model_validate",
    "model_validate_json",
    "model_validate_strings",
    "model_construct",
    "model_copy",
    "model_dump",
    "model_dump_json",
})


def _color_marker(color: str, text: Any) -> str:
    """Возвращает строку, обёрнутую в цветовой маркер."""
    return f"__COLOR({color}){text}__COLOR_END__"


# ----------------------------------------------------------------------
# Вспомогательные функции интроспекции для debug()
# ----------------------------------------------------------------------


def _is_pydantic_class_attr(obj: Any, name: str) -> bool:
    """
    Проверяет, является ли имя pydantic-специфичным class-level атрибутом.

    Обращение к таким атрибутам через экземпляр вызывает
    DeprecationWarning в Pydantic V2.11+.

    Аргументы:
        obj: объект для проверки.
        name: имя атрибута.

    Возвращает:
        True если атрибут является pydantic class-level атрибутом.
    """
    if isinstance(obj, BaseModel) and name in _PYDANTIC_CLASS_ATTRS:
        return True
    return False


def _is_public_data_attribute(obj: Any, name: str) -> bool:
    """
    Определяет, является ли имя публичным атрибутом данных.

    Исключает:
    - Имена, начинающиеся с подчёркивания.
    - Методы (callable).
    - Pydantic class-level атрибуты.

    Аргументы:
        obj: объект для проверки.
        name: имя атрибута.

    Возвращает:
        True если это публичный атрибут данных.
    """
    if name.startswith('_'):
        return False
    if _is_pydantic_class_attr(obj, name):
        return False
    try:
        attr = getattr(obj, name)
        if callable(attr):
            return False
    except Exception:
        return False
    return True


def _is_public_property(obj: Any, name: str) -> bool:
    """
    Проверяет, является ли имя публичным свойством (property).

    Исключает имена, начинающиеся с подчёркивания, и pydantic
    class-level атрибуты.

    Аргументы:
        obj: объект для проверки.
        name: имя атрибута.

    Возвращает:
        True если это публичное свойство.
    """
    if name.startswith('_'):
        return False
    if _is_pydantic_class_attr(obj, name):
        return False
    for base in type(obj).__mro__:
        if name in base.__dict__:
            member = base.__dict__[name]
            if isinstance(member, property):
                return True
    return False


def _get_sensitive_config(obj: Any, name: str) -> dict[str, Any] | None:
    """
    Возвращает конфигурацию @sensitive, если свойство имеет этот декоратор.

    Аргументы:
        obj: объект, содержащий свойство.
        name: имя свойства.

    Возвращает:
        dict с конфигурацией маскирования или None.
    """
    for base in type(obj).__mro__:
        if name in base.__dict__:
            member = base.__dict__[name]
            if isinstance(member, property) and member.fget and hasattr(member.fget, "_sensitive_config"):
                return member.fget._sensitive_config  # type: ignore[no-any-return]
    return None


def _format_value(value: Any) -> str:
    """
    Возвращает безопасное строковое представление значения.

    Аргументы:
        value: значение для форматирования.

    Возвращает:
        Строковое представление через repr.
    """
    try:
        return repr(value)
    except Exception:
        return "<unprintable>"


def _inspect_collection(obj: Any, indent_str: str, type_name: str) -> str:
    """Интроспекция списка, кортежа или множества."""
    if len(obj) == 0:
        return f"{indent_str}{type_name}[]"
    preview = _format_value(list(obj)[:3])
    if len(obj) > 3:
        preview = preview[:-1] + ", ...]"
    return f"{indent_str}{type_name}{preview}"


def _inspect_dict(obj: dict[str, Any], indent_str: str, type_name: str) -> str:
    """Интроспекция словаря."""
    if len(obj) == 0:
        return f"{indent_str}{type_name}{{}}"
    lines = [f"{indent_str}{type_name}:"]
    for k, v in list(obj.items())[:10]:
        lines.append(f"{indent_str}  {_format_value(k)}: {_format_value(v)}")
    if len(obj) > 10:
        lines.append(f"{indent_str}  ... and {len(obj)-10} more")
    return "\n".join(lines)


def _is_custom_object(value: Any) -> bool:
    """
    Определяет, является ли значение пользовательским объектом
    (не встроенным примитивом и не коллекцией).

    Аргументы:
        value: значение для проверки.

    Возвращает:
        True если объект не является str, int, float, bool, None,
        list, tuple, dict или set.
    """
    return isinstance(value, object) and not isinstance(
        value, (str, int, float, bool, type(None), list, tuple, dict, set)
    )


def _format_field_line(
    obj: Any, name: str, value: Any, indent_str: str,
    visited: set[int], max_depth: int, indent: int,
) -> str:
    """
    Форматирует одну строку поля для вывода debug.

    Проверка циклических ссылок выполняется ПЕРЕД проверкой max_depth.
    Это гарантирует обнаружение циклов даже при max_depth=1, когда
    рекурсия в глубину не происходит. Без этой проверки циклические
    ссылки на первом уровне отображались бы как repr(value) вместо
    <cycle detected>.

    Аргументы:
        obj: родительский объект (для проверки @sensitive).
        name: имя поля.
        value: значение поля.
        indent_str: текущий отступ.
        visited: множество id уже обработанных объектов.
        max_depth: оставшаяся глубина рекурсии.
        indent: числовой уровень отступа.

    Возвращает:
        Одну или несколько строк для вывода.
    """
    # Проверка циклов ДО проверки max_depth — ключевой инвариант.
    if _is_custom_object(value) and id(value) in visited:
        return f"{indent_str}  {name}: <cycle detected>"

    config = _get_sensitive_config(obj, name)

    if config and config.get('enabled', True):
        masked = mask_value(value, config)
        type_str = type(value).__name__
        suffix = (
            f" (sensitive: enabled, max_chars={config.get('max_chars', 3)}, "
            f"char='{config.get('char', '*')}', "
            f"max_percent={config.get('max_percent', 50)})"
        )
        value_str = masked
    elif config and not config.get('enabled', True):
        type_str = type(value).__name__
        suffix = " (sensitive: disabled)"
        value_str = _format_value(value)
    else:
        type_str = type(value).__name__
        suffix = ""
        value_str = _format_value(value)

    if max_depth > 1 and _is_custom_object(value):
        inner = _inspect_object(value, indent + 2, visited, max_depth - 1)
        return f"{indent_str}  {name}: {type_str}{suffix}\n{inner}"
    return f"{indent_str}  {name}: {type_str}{suffix} = {value_str}"


def _inspect_custom(
    obj: Any, indent_str: str, type_name: str,
    visited: set[int], max_depth: int, indent: int,
) -> str:
    """Интроспекция пользовательского объекта (не встроенной коллекции)."""
    data_attrs = {}
    for name in dir(obj):
        if _is_public_data_attribute(obj, name):
            try:
                data_attrs[name] = getattr(obj, name)
            except Exception:
                continue

    props = {}
    for name in dir(obj):
        if _is_public_property(obj, name):
            try:
                props[name] = getattr(obj, name)
            except Exception:
                continue

    # --- Добавлено: извлечение extra-полей из Pydantic моделей с extra="allow" ---
    if hasattr(obj, "__pydantic_extra__") and isinstance(obj.__pydantic_extra__, dict):
        for key, value in obj.__pydantic_extra__.items():
            if key.startswith('_'):
                continue
            if key in data_attrs or key in props:
                continue   # регулярный атрибут имеет приоритет
            data_attrs[key] = value
    # -------------------------------------------------------------------------

    all_fields = {**data_attrs, **props}

    if not all_fields:
        return f"{indent_str}{type_name}: (no public fields)"

    lines = [f"{indent_str}{type_name}:"]
    for name, value in all_fields.items():
        lines.append(
            _format_field_line(obj, name, value, indent_str, visited, max_depth, indent)
        )

    return "\n".join(lines)


def _inspect_object(
    obj: Any, indent: int = 0,
    visited: set[int] | None = None, max_depth: int = 1,
) -> str:
    """
    Рекурсивно строит строковое представление публичных полей объекта.

    Добавляет id текущего объекта в visited ДО обхода полей. Это
    гарантирует, что если поле ссылается обратно на текущий объект
    (или на любой объект выше по цепочке), _format_field_line обнаружит
    цикл через проверку id(value) in visited.

    Аргументы:
        obj: объект для интроспекции.
        indent: текущий уровень отступа (количество пробелов).
        visited: множество id уже обработанных объектов (защита от циклов).
        max_depth: максимальная глубина рекурсии. По умолчанию 1 (только
                   непосредственные поля). При max_depth > 1 вложенные
                   объекты раскрываются рекурсивно.

    Возвращает:
        Форматированная многострочная строка.
    """
    if visited is None:
        visited = set()

    obj_id = id(obj)
    if obj_id in visited:
        return f"{' ' * indent}<cycle detected>"
    visited.add(obj_id)

    indent_str = " " * indent
    type_name = type(obj).__name__

    # Базовые типы
    if isinstance(obj, (str, int, float, bool, type(None))):
        return f"{indent_str}{type_name} = {_format_value(obj)}"

    # Коллекции
    if isinstance(obj, (list, tuple, set)):
        return _inspect_collection(obj, indent_str, type_name)
    if isinstance(obj, dict):
        return _inspect_dict(obj, indent_str, type_name)

    # Пользовательские объекты
    return _inspect_custom(obj, indent_str, type_name, visited, max_depth, indent)


def debug_value(obj: Any) -> str:
    """
    Возвращает форматированное строковое представление объекта для debug-вывода.

    Обёртка над _inspect_object с max_depth=1. Предназначена для
    использования как фильтр в шаблонах: {%var.user|debug}
    или как функция внутри iif: debug(var.user).

    Вывод показывает только непосредственные поля (без рекурсии),
    чтобы не засорять логи. Для интроспекции вложенных объектов
    вызывайте debug на вложенном атрибуте напрямую.

    Аргументы:
        obj: объект для интроспекции.

    Возвращает:
        Форматированная строка с полями объекта.
    """
    return _inspect_object(obj, max_depth=1)


# ----------------------------------------------------------------------
# Безопасные функции для вычислителя выражений (базовый набор, без exists)
# ----------------------------------------------------------------------

_BASE_SAFE_FUNCTIONS: dict[str, Any] = {
    "len": len,
    "upper": lambda s: str(s).upper(),
    "lower": lambda s: str(s).lower(),
    "str": str,
    "int": int,
    "float": float,
    "abs": abs,
    "format_number": lambda n, decimals=2: f"{float(n):,.{int(decimals)}f}",
    "red": lambda text: _color_marker("red", text),
    "green": lambda text: _color_marker("green", text),
    "yellow": lambda text: _color_marker("yellow", text),
    "blue": lambda text: _color_marker("blue", text),
    "magenta": lambda text: _color_marker("magenta", text),
    "cyan": lambda text: _color_marker("cyan", text),
    "white": lambda text: _color_marker("white", text),
    "grey": lambda text: _color_marker("grey", text),
    "debug": lambda obj: _inspect_object(obj, max_depth=1),
}


class _IifArgSplitter:
    """
    Разбивает аргументы iif по ';' с учётом вложенных скобок
    и строковых литералов.

    Простой split(';') не работает, потому что могут быть вложенные iif
    или строки, содержащие ';'.

    Принцип работы:
    1. Итерация по символам входной строки.
    2. Если внутри строкового литерала — накапливаем символы до закрывающей кавычки.
    3. Если встречена открывающая кавычка — входим в режим строкового литерала.
    4. Иначе обрабатываем структурные символы: скобки меняют глубину,
       ';' на глубине 0 разделяет аргументы.
    """

    def __init__(self, raw: str) -> None:
        """
        Инициализирует разборщик.

        Аргументы:
            raw: строка аргументов без внешних скобок.
                 Пример: "amount > 1000; 'HIGH'; 'LOW'".
        """
        self._raw = raw
        self._parts: list[str] = []
        self._current: list[str] = []
        self._depth: int = 0
        self._in_string: bool = False
        self._string_char: str = ""

    def _handle_string_char(self, char: str) -> bool:
        """
        Обрабатывает символ внутри строкового литерала.

        Внутри строки все символы накапливаются без интерпретации.
        Единственный особый символ — закрывающая кавычка.

        Аргументы:
            char: текущий символ.

        Возвращает:
            True если символ обработан (мы внутри строки).
        """
        if not self._in_string:
            return False
        self._current.append(char)
        if char == self._string_char:
            self._in_string = False
        return True

    def _handle_quote(self, char: str) -> bool:
        """
        Обрабатывает открывающую кавычку (одинарную или двойную).

        Аргументы:
            char: текущий символ.

        Возвращает:
            True если символ — кавычка и обработан.
        """
        if char not in ("'", '"'):
            return False
        self._in_string = True
        self._string_char = char
        self._current.append(char)
        return True

    def _handle_structural_char(self, char: str) -> None:
        """
        Обрабатывает структурные символы: скобки и разделитель ';'.

        '(' увеличивает глубину вложенности.
        ')' уменьшает глубину вложенности.
        ';' на глубине 0 завершает текущий аргумент и начинает новый.
        На ненулевой глубине ';' является частью вложенного выражения.
        """
        if char == "(":
            self._depth += 1
            self._current.append(char)
        elif char == ")":
            self._depth -= 1
            self._current.append(char)
        elif char == ";" and self._depth == 0:
            self._parts.append("".join(self._current))
            self._current = []
        else:
            self._current.append(char)

    def split(self) -> list[str]:
        """
        Разбивает строку аргументов и возвращает список частей.

        Возвращает:
            Список строк — аргументы iif (в идеале 3 для корректного iif).
        """
        for char in self._raw:
            if self._handle_string_char(char):
                continue
            if self._handle_quote(char):
                continue
            self._handle_structural_char(char)

        if self._current:
            self._parts.append("".join(self._current))

        return self._parts


class ExpressionEvaluator:
    """
    Безопасный вычислитель выражений для шаблонов логирования.

    Оборачивает simpleeval, предоставляя:
    - Набор безопасных функций (len, upper, lower, format_number,
      цветовые функции, debug, exists).
    - Защиту от выполнения произвольного кода.
    - Метод evaluate для одиночных выражений.
    - Метод evaluate_iif для конструкций iif.
    - Метод process_template для обработки всех {iif(...)} в шаблоне.

    Ошибки НЕ подавляются. Невалидное выражение → LogTemplateError.

    Секреты в логах: помечайте поля ``@sensitive``; ``debug()`` может вывести
    много данных, если в выражение передан крупный объект из контекста.
    """

    def evaluate(self, expression: str, names: dict[str, Any]) -> Any:
        """
        Вычисляет одиночное выражение в контексте переменных.

        Аргументы:
            expression: строка выражения в стиле Python.
            names: словарь переменных, доступных в выражении.

        Возвращает:
            Результат вычисления (любой тип).

        Исключения:
            LogTemplateError: если выражение невалидно или содержит
                неопределённые переменные.
        """
        def exists(name: str) -> bool:
            """Проверяет наличие переменной в текущем контексте."""
            return name in names

        functions = dict(_BASE_SAFE_FUNCTIONS)
        functions["exists"] = exists

        evaluator = EvalWithCompoundTypes(
            names=names,
            functions=functions,
        )
        try:
            return evaluator.eval(expression)
        except NameNotDefined as e:
            raise LogTemplateError(
                f"Variable '{e.name}' not found in expression '{expression}'"
            ) from e
        except Exception as e:
            raise LogTemplateError(
                f"Error evaluating expression '{expression}': {e}"
            ) from e

    def evaluate_iif(
        self,
        raw_args: str,
        names: dict[str, Any],
    ) -> str:
        """
        Вычисляет конструкцию iif(condition; true_branch; false_branch).

        Разбивает строку аргументов по ';', вычисляет условие
        и возвращает выбранную ветку как строку.

        Важно: template-level вложенные ``{iif(...)}`` не поддерживаются.
        Разрешён только один внешний ``{iif(...)}`` в process_template().
        Рекурсивная обработка ниже применяется к строке выбранной ветки,
        если она имеет форму ``iif(...)`` без внешних фигурных скобок.

        Аргументы:
            raw_args: строка вида "condition; true_value; false_value".
            names: словарь переменных для подстановки.

        Возвращает:
            Строковый результат выбранной ветки.

        Исключения:
            LogTemplateError: если число аргументов iif не равно 3,
                ошибка вычисления условия или ветки.
        """
        processed_args = self.process_template(raw_args, names)
        parts = self._split_iif_args(processed_args)

        if len(parts) != 3:
            raise LogTemplateError(
                f"iif expects 3 arguments separated by ';', got {len(parts)}. "
                f"Expression: iif({raw_args})"
            )

        condition_str = parts[0].strip()
        true_expr = parts[1].strip()
        false_expr = parts[2].strip()

        condition_result = self.evaluate(condition_str, names)
        chosen_expr = true_expr if condition_result else false_expr

        stripped = chosen_expr.strip()
        if stripped.startswith("iif(") and stripped.endswith(")"):
            inner_args = stripped[4:-1]
            return self.evaluate_iif(inner_args, names)

        result = self.evaluate(chosen_expr, names)
        return str(result)

    def process_template(
        self,
        template: str,
        names: dict[str, Any],
    ) -> str:
        """
        Обрабатывает все вхождения {iif(...)} в строке шаблона.

        Находит каждое ``{iif(...)}``, вычисляет через evaluate_iif
        и подставляет результат.

        Ограничение: вложенные template-level конструкции вида
        ``{iif(...{iif(...)}...)}`` не входят в grammar этого метода.

        Аргументы:
            template: строка шаблона с конструкциями {iif(...)}.
            names: словарь переменных для подстановки.

        Возвращает:
            Строка со всеми iif, заменёнными на вычисленные результаты.

        Исключения:
            LogTemplateError: если любое iif-выражение невалидно.
        """
        def replacer(match: re.Match[str]) -> str:
            raw_args = match.group(1)
            return self.evaluate_iif(raw_args, names)

        return _IIF_PATTERN.sub(replacer, template)

    def _split_iif_args(self, raw: str) -> list[str]:
        """
        Разбивает аргументы iif через _IifArgSplitter.

        Аргументы:
            raw: строка аргументов без внешних скобок iif.

        Возвращает:
            Список частей (в идеале 3 для корректного iif).
        """
        return _IifArgSplitter(raw).split()
