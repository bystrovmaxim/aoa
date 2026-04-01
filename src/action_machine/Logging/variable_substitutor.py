# src/action_machine/logging/variable_substitutor.py
"""
Подстановщик переменных для шаблонов логирования ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

VariableSubstitutor отвечает за:

1. Разрешение переменных {%namespace.dotpath} из пяти источников:
   - var — словарь пользовательских переменных.
   - state — текущее состояние конвейера (BaseState).
   - scope — LogScope (местоположение в конвейере).
   - context — контекст выполнения (ReadableMixin).
   - params — входные параметры действия (ReadableMixin).

2. Двухпроходную подстановку:
   - Проход 1: замена {%namespace.path} на значения.
     Внутри {iif(...)} значения подставляются как литералы
     (строки в кавычках, числа как есть).
   - Проход 2: вычисление {iif(...)} через ExpressionEvaluator.

3. Строгую политику ошибок:
   - Переменная не найдена → LogTemplateError.
   - Неизвестный namespace → LogTemplateError.
   - Невалидный iif → LogTemplateError.
   - Обращение к имени с подчёркиванием → LogTemplateError.

4. Цветовые фильтры: синтаксис {%var.amount|red} (вне iif) и цветовые
   функции red('text') (внутри iif). Преобразуются в маркеры, затем
   заменяются на ANSI-коды.

5. Debug-фильтр: синтаксис {%var.obj|debug} выводит форматированную
   интроспекцию объекта (публичные поля и свойства).

6. Маскирование чувствительных данных: если разрешённая переменная
   является свойством с декоратором @sensitive, значение маскируется
   по параметрам декоратора.

═══════════════════════════════════════════════════════════════════════════════
ОБРАБОТКА ЦВЕТОВЫХ МАРКЕРОВ
═══════════════════════════════════════════════════════════════════════════════

Цветовые маркеры имеют вид __COLOR(color)content__COLOR_END__. При
вложенных цветах (например, red('level: ' + green('ok'))) возникают
вложенные маркеры:

    __COLOR(red)level: __COLOR(green)ok__COLOR_END____COLOR_END__

Метод _apply_color_filters обрабатывает маркеры ИЗНУТРИ НАРУЖУ:
паттерн захватывает только маркеры без вложенных __COLOR( внутри,
и применяется в цикле до тех пор, пока маркеры остаются. Это
гарантирует корректную обработку любой глубины вложенности.

═══════════════════════════════════════════════════════════════════════════════
ПОДДЕРЖИВАЕМЫЕ ЦВЕТА
═══════════════════════════════════════════════════════════════════════════════

Имя цвета может быть:
- Простой foreground: "red", "green", "blue", "yellow", "magenta",
  "cyan", "white", "grey", "orange", "bright_green" и т.д.
- Background с префиксом "bg_": "bg_red", "bg_blue".
- Комбинация "foreground_on_background": "red_on_blue", "green_on_black".

Неизвестное имя цвета → LogTemplateError.

═══════════════════════════════════════════════════════════════════════════════
ЕДИНСТВЕННЫЙ ПУБЛИЧНЫЙ МЕТОД
═══════════════════════════════════════════════════════════════════════════════

substitute() — принимает шаблон и все источники данных, выполняет
подстановку и возвращает финальную строку. LogCoordinator вызывает
substitute() вместо собственной реализации.
"""

import re
from collections.abc import Callable
from typing import Any

from action_machine.context.context import Context
from action_machine.core.base_params import BaseParams
from action_machine.core.base_state import BaseState
from action_machine.core.exceptions import LogTemplateError
from action_machine.core.readable_mixin import ReadableMixin
from action_machine.logging.expression_evaluator import ExpressionEvaluator, debug_value
from action_machine.logging.log_scope import LogScope
from action_machine.logging.masking import mask_value

# ---------------------------------------------------------------------------
# Регулярные выражения
# ---------------------------------------------------------------------------
# Формат: {%namespace} или {%namespace.dotpath} с опциональным |color или |debug
# Группа 1 (namespace): источник данных (var, state, scope, context, params).
# Группа 2 (опциональный путь): dot-path внутри источника (может быть None).
# Группа 3 (опциональный фильтр): имя цвета или "debug".
_VARIABLE_PATTERN: re.Pattern[str] = re.compile(
    r"\{%([a-zA-Z_][a-zA-Z0-9_]*)\.?([a-zA-Z_][a-zA-Z0-9_.]*)?(?:\|([a-zA-Z_]+))?\}"
)
# Используется для обнаружения блоков iif, чтобы внутри них подставлять
# значения как литералы.
_IIF_BLOCK_PATTERN: re.Pattern[str] = re.compile(r"\{iif\(.*?\)\}")

# Сентинел для отличия «атрибут не найден» от «атрибут равен None».
_SENTINEL: object = object()

# ---------------------------------------------------------------------------
# ANSI-коды цветов для foreground и background (8 базовых + bright-варианты)
# ---------------------------------------------------------------------------
_FG_COLORS: dict[str, str] = {
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "grey": "90",
    "orange": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}

_BG_COLORS: dict[str, str] = {
    "black": "40",
    "red": "41",
    "green": "42",
    "yellow": "43",
    "blue": "44",
    "magenta": "45",
    "cyan": "46",
    "white": "47",
    "grey": "100",
    "orange": "101",
    "bright_green": "102",
    "bright_yellow": "103",
    "bright_blue": "104",
    "bright_magenta": "105",
    "bright_cyan": "106",
    "bright_white": "107",
}

_RESET_CODE: str = "\033[0m"


class VariableSubstitutor:
    """
    Подстановщик переменных и вычислитель iif для шаблонов логирования.

    Содержит всю логику:
    - Разрешение переменных из пяти namespace через dispatch-словарь.
    - Навигация по вложенным объектам через dot-path с помощью _resolve_one_step.
    - Форматирование значений как литералов для simpleeval
      (строки в кавычках, числа как есть).
    - Двухпроходная подстановка: сначала {%...}, затем {iif(...)}.
    - Строгая обработка ошибок: подчёркивания → LogTemplateError.
    - Цветовые фильтры через |color (вне iif) и цветовые функции (внутри iif),
      преобразуемые в маркеры и постобрабатываемые в ANSI-коды.
    - Debug-фильтр через |debug, выводящий интроспекцию объекта.
    - Маскирование @sensitive-свойств.

    Атрибуты:
        _evaluator: экземпляр ExpressionEvaluator для вычисления iif.
        _namespace_resolvers: dispatch-словарь namespace → метод-резольвер.
    """

    def __init__(self) -> None:
        """Инициализирует подстановщик с вычислителем и резольверами."""
        self._evaluator: ExpressionEvaluator = ExpressionEvaluator()
        self._namespace_resolvers: dict[
            str,
            Callable[
                [str, dict[str, Any], LogScope, Context, BaseState, BaseParams],
                tuple[object, object | None],
            ],
        ] = {
            "var": self._resolve_ns_var,
            "state": self._resolve_ns_state,
            "scope": self._resolve_ns_scope,
            "context": self._resolve_ns_context,
            "params": self._resolve_ns_params,
        }

    # ----------------------------------------------------------------
    # Навигация по вложенным объектам (аналог ReadableMixin._resolve_one_step)
    # ----------------------------------------------------------------

    @staticmethod
    def _resolve_step_readable(
        current: ReadableMixin,
        segment: str,
    ) -> object:
        """Шаг навигации для объектов с ReadableMixin (через __getitem__)."""
        try:
            return current[segment]
        except KeyError:
            return _SENTINEL

    @staticmethod
    def _resolve_step_dict(
        current: dict[str, object],
        segment: str,
    ) -> object:
        """Шаг навигации для обычных словарей."""
        if segment in current:
            return current[segment]
        return _SENTINEL

    @staticmethod
    def _resolve_step_generic(
        current: object,
        segment: str,
    ) -> object:
        """Шаг навигации для произвольных объектов через getattr."""
        return getattr(current, segment, _SENTINEL)

    def _resolve_one_step(
        self,
        current: object,
        segment: str,
    ) -> object:
        """
        Выполняет один шаг навигации, выбирая стратегию по типу объекта.

        Приоритет стратегий:
            1. ReadableMixin — __getitem__.
            2. dict — прямой доступ по ключу.
            3. Любой другой объект — getattr.

        Аргументы:
            current: текущий объект на этом шаге навигации.
            segment: имя ключа/атрибута для перехода.

        Возвращает:
            Найденное значение или _SENTINEL если шаг не удался.
        """
        if isinstance(current, ReadableMixin):
            return self._resolve_step_readable(current, segment)
        if isinstance(current, dict):
            return self._resolve_step_dict(current, segment)
        return self._resolve_step_generic(current, segment)

    def _resolve_path(
        self,
        start: object,
        path: str,
    ) -> tuple[object, object | None]:
        """
        Разрешает dot-path от заданного объекта.

        Возвращает кортеж (value, source_object), где source_object —
        объект, из которого был взят последний сегмент пути (нужен
        для обнаружения @sensitive-свойств).

        Аргументы:
            start: начальный объект.
            path: dot-separated путь.

        Возвращает:
            (value, source) или (_SENTINEL, None) при неудаче.
        """
        if not path:
            return start, None

        segments = path.split(".")
        current = start
        source = None

        for segment in segments:
            source = current
            current = self._resolve_one_step(current, segment)
            if current is _SENTINEL:
                return _SENTINEL, None
        return current, source

    # ----------------------------------------------------------------
    # Namespace-резольверы (используют _resolve_path)
    # ----------------------------------------------------------------

    def _resolve_ns_var(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None]:
        """Разрешает переменную из словаря var."""
        return self._resolve_path(var, path)

    def _resolve_ns_state(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None]:
        """Разрешает переменную из BaseState."""
        return self._resolve_path(state, path)

    def _resolve_ns_scope(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None]:
        """Разрешает переменную из LogScope."""
        return self._resolve_path(scope, path)

    def _resolve_ns_context(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None]:
        """Разрешает переменную из Context."""
        return self._resolve_path(ctx, path)

    def _resolve_ns_params(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None]:
        """Разрешает переменную из BaseParams."""
        return self._resolve_path(params, path)

    # ----------------------------------------------------------------
    # Обнаружение и маскирование @sensitive-свойств
    # ----------------------------------------------------------------

    def _get_property_config(self, obj: object, attr_name: str) -> dict[str, Any] | None:
        """
        Проверяет, имеет ли свойство attr_name на объекте obj декоратор @sensitive.

        Обходит MRO класса объекта, ищет property с _sensitive_config на getter.

        Аргументы:
            obj: объект-источник атрибута.
            attr_name: имя атрибута.

        Возвращает:
            dict с конфигурацией маскирования или None.
        """
        if obj is None:
            return None
        cls = type(obj)
        for base in cls.__mro__:
            if attr_name in base.__dict__:
                prop = base.__dict__[attr_name]
                if isinstance(prop, property):
                    fget = prop.fget
                    if fget is not None and hasattr(fget, "_sensitive_config"):
                        return fget._sensitive_config  # type: ignore[no-any-return]
        return None

    # ----------------------------------------------------------------
    # Разрешение переменной (сырое значение, без строкового преобразования)
    # ----------------------------------------------------------------

    def _resolve_variable_raw(
        self,
        namespace: str,
        path: str | None,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> tuple[object, object | None]:
        """
        Разрешает одну переменную из шаблона — сырое значение и объект-источник.

        Использует dispatch-словарь _namespace_resolvers.
        Неизвестный namespace → LogTemplateError.

        Аргументы:
            namespace: первый сегмент переменной ("var", "context", ...).
            path: оставшийся dot-path после namespace (может быть None).
            var, scope, ctx, state, params: источники данных.

        Возвращает:
            Кортеж (raw_value, source_object).

        Исключения:
            LogTemplateError: если namespace неизвестен.
        """
        resolver = self._namespace_resolvers.get(namespace)
        if resolver is None:
            raise LogTemplateError(
                f"Unknown namespace '{namespace}' in template. "
                f"Allowed: {', '.join(sorted(self._namespace_resolvers))}. "
                f"Check variable {{%{namespace}.{path or ''}}}."
            )
        return resolver(path or "", var, scope, ctx, state, params)

    # ----------------------------------------------------------------
    # Строковое разрешение с проверкой None, подчёркиваний и маскированием
    # ----------------------------------------------------------------

    def _resolve_variable(
        self,
        namespace: str,
        path: str | None,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> str:
        """
        Разрешает одну переменную — возвращает строковое представление,
        возможно замаскированное.
        """
        last_segment = None
        if path is not None:
            last_segment = path.split(".")[-1]
            if last_segment.startswith("_"):
                raise LogTemplateError(
                    f"Access to name starting with underscore is forbidden: '{last_segment}' "
                    f"in variable {{%{namespace}.{path}}}. Use a public property if output is needed."
                )

        raw_value, source = self._resolve_variable_raw(
            namespace, path, var, scope, ctx, state, params
        )
        if raw_value is _SENTINEL:
            raise LogTemplateError(
                f"Variable '{{%{namespace}.{path or ''}}}' not found. "
                f"Check the template and ensure the value exists in source '{namespace}'."
            )

        config = None
        if source is not None and last_segment is not None:
            config = self._get_property_config(source, last_segment)

        if config:
            if not config.get('enabled', True):
                return str(raw_value)
            return mask_value(raw_value, config)

        return str(raw_value)

    # ----------------------------------------------------------------
    # Форматирование значений как литералов для iif
    # ----------------------------------------------------------------

    @staticmethod
    def _quote_if_string(raw_value: object) -> str:
        """
        Форматирует сырое значение как литерал для simpleeval.

        Числа и булевы значения возвращаются как строки без кавычек.
        Строки оборачиваются в одинарные кавычки.
        Цветовые маркеры (__COLOR(...)) возвращаются без кавычек,
        чтобы сохранить маркер для последующей обработки.

        Аргументы:
            raw_value: сырое значение.

        Возвращает:
            Строка, пригодная для вставки в выражение simpleeval.
        """
        if isinstance(raw_value, bool):
            return str(raw_value)
        if isinstance(raw_value, (int, float)):
            return str(raw_value)
        s = str(raw_value)
        if "__COLOR(" in s and "__COLOR_END__" in s:
            return s
        s = s.replace("'", "\\'")
        return f"'{s}'"

    # ----------------------------------------------------------------
    # Подстановка переменных — три приватных метода
    # ----------------------------------------------------------------

    def _substitute_simple(
        self,
        message: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> str:
        """
        Быстрый путь: нет iif — простая замена {%...} → str(value).
        Обрабатывает цветовые фильтры (|color) и debug-фильтр (|debug).
        """
        def replacer(match: re.Match[str]) -> str:
            namespace = match.group(1)
            path = match.group(2)
            filter_name = match.group(3)
            value = self._resolve_variable(
                namespace, path, var, scope, ctx, state, params
            )

            if filter_name == "debug":
                raw_value, _ = self._resolve_variable_raw(
                    namespace, path, var, scope, ctx, state, params
                )
                return debug_value(raw_value)
            if filter_name:
                return f"__COLOR({filter_name}){value}__COLOR_END__"
            return value

        return _VARIABLE_PATTERN.sub(replacer, message)

    def _format_variable_for_template(
        self,
        match: re.Match[str],
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        inside_iif: bool,
    ) -> str:
        """
        Форматирует одно вхождение переменной в шаблоне, учитывая
        маскировку, фильтры и нахождение внутри/вне iif.
        """
        namespace = match.group(1)
        path = match.group(2)
        filter_name = match.group(3)
        raw_value, source = self._resolve_variable_raw(
            namespace, path, var, scope, ctx, state, params
        )
        if raw_value is _SENTINEL:
            raise LogTemplateError(
                f"Variable '{{%{namespace}.{path or ''}}}' not found. "
                f"Check the template and ensure the value exists in source '{namespace}'."
            )

        last_segment = None
        if path is not None:
            last_segment = path.split(".")[-1]

        config = None
        if source is not None and last_segment is not None:
            config = self._get_property_config(source, last_segment)

        if inside_iif:
            if config:
                str_value = mask_value(raw_value, config)
            else:
                str_value = str(raw_value)
            if isinstance(raw_value, (bool, int, float)):
                formatted = str_value
            else:
                formatted = self._quote_if_string(str_value)
        else:
            if config:
                formatted = mask_value(raw_value, config)
            else:
                formatted = str(raw_value)

        if filter_name == "debug":
            return debug_value(raw_value)
        if filter_name:
            return f"__COLOR({filter_name}){formatted}__COLOR_END__"
        return formatted

    def _substitute_with_iif_detection(
        self,
        message: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> str:
        """
        Медленный путь: есть iif — определяет позицию каждой переменной
        относительно блоков iif и форматирует соответственно.
        """
        iif_ranges = [
            (m.start(), m.end())
            for m in _IIF_BLOCK_PATTERN.finditer(message)
        ]

        def _inside_iif(pos: int) -> bool:
            return any(start <= pos < end for start, end in iif_ranges)

        def replacer(match: re.Match[str]) -> str:
            inside = _inside_iif(match.start())
            return self._format_variable_for_template(
                match, var, scope, ctx, state, params, inside
            )

        return _VARIABLE_PATTERN.sub(replacer, message)

    def _substitute_variables(
        self,
        message: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        has_iif: bool,
    ) -> str:
        """
        Диспетчер первого прохода: выбирает стратегию подстановки.

        Если шаблон содержит iif — медленный путь с определением позиций.
        Иначе — быстрый путь.
        """
        if has_iif:
            return self._substitute_with_iif_detection(
                message, var, scope, ctx, state, params
            )
        return self._substitute_simple(message, var, scope, ctx, state, params)

    # ----------------------------------------------------------------
    # Постобработка цветовых маркеров → ANSI-коды
    # ----------------------------------------------------------------

    def _resolve_color_name(self, color_name: str) -> str:
        """
        Преобразует имя цвета в ANSI-код.

        Поддерживает три формата:
        - "bg_<color>" — только фон.
        - "<fg>_on_<bg>" — foreground + background.
        - "<color>" — только foreground.

        Аргументы:
            color_name: имя цвета из маркера.

        Возвращает:
            ANSI escape-последовательность (например, "\\033[31m").

        Исключения:
            LogTemplateError: если имя цвета неизвестно.
        """
        if color_name.startswith("bg_"):
            bg_name = color_name[3:]
            bg_code = _BG_COLORS.get(bg_name)
            if bg_code is None:
                raise LogTemplateError(f"Unknown background color: '{bg_name}'")
            return f"\033[{bg_code}m"

        if "_on_" in color_name:
            parts = color_name.split("_on_", 1)
            if len(parts) != 2:
                raise LogTemplateError(
                    f"Invalid color format: '{color_name}'. "
                    f"Use 'foreground_on_background'."
                )
            fg_name, bg_name = parts
            fg_code = _FG_COLORS.get(fg_name)
            bg_code = _BG_COLORS.get(bg_name)
            if fg_code is None:
                raise LogTemplateError(f"Unknown foreground color: '{fg_name}'")
            if bg_code is None:
                raise LogTemplateError(f"Unknown background color: '{bg_name}'")
            return f"\033[{fg_code};{bg_code}m"

        fg_code = _FG_COLORS.get(color_name)
        if fg_code is None:
            raise LogTemplateError(f"Unknown color: '{color_name}'")
        return f"\033[{fg_code}m"

    def _apply_color_filters(self, text: str) -> str:
        """
        Заменяет цветовые маркеры на ANSI-коды.

        Обрабатывает маркеры ИЗНУТРИ НАРУЖУ: паттерн захватывает только
        маркеры, не содержащие вложенных __COLOR( внутри контента.
        Цикл повторяется, пока в строке остаются маркеры. Это гарантирует
        корректную обработку вложенных цветов любой глубины.

        Пример вложенных маркеров:
            __COLOR(red)level: __COLOR(green)ok__COLOR_END____COLOR_END__
        Первая итерация обрабатывает внутренний:
            __COLOR(red)level: \\033[32mok\\033[0m__COLOR_END__
        Вторая итерация обрабатывает внешний:
            \\033[31mlevel: \\033[32mok\\033[0m\\033[0m

        Аргументы:
            text: строка с цветовыми маркерами.

        Возвращает:
            Строка с ANSI-кодами вместо маркеров.

        Исключения:
            LogTemplateError: если имя цвета неизвестно.
        """
        # Паттерн захватывает маркер, контент которого НЕ содержит
        # вложенных __COLOR(. Это заставляет обработку идти изнутри наружу.
        pattern = re.compile(
            r"__COLOR\(([a-zA-Z_]+)\)((?:(?!__COLOR\().)*)__COLOR_END__",
            re.DOTALL,
        )

        while pattern.search(text):
            def replacer(match: re.Match[str]) -> str:
                color_name = match.group(1)
                content = match.group(2)
                ansi_code = self._resolve_color_name(color_name)
                return f"{ansi_code}{content}{_RESET_CODE}"

            text = pattern.sub(replacer, text)

        return text

    # ----------------------------------------------------------------
    # Единственный публичный метод
    # ----------------------------------------------------------------

    def substitute(
        self,
        message: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> str:
        """
        Выполняет все подстановки переменных и вычисление iif.

        Три прохода:

        1. Подстановка {%namespace.dotpath} во всём шаблоне, включая
           внутри {iif(...)}. Внутри iif значения форматируются как
           литералы (строки в кавычках, числа и булевы как есть).
           Цветовые фильтры (|color) превращаются в маркеры.
           Debug-фильтр (|debug) выводит интроспекцию объекта.

        2. Вычисление {iif(...)} через ExpressionEvaluator. simpleeval
           получает выражения с уже подставленными литералами и пустой
           словарь имён. Цветовые функции (red('text')) внутри iif
           возвращают маркеры.

        3. Постобработка цветовых маркеров: замена __COLOR(...)...__COLOR_END__
           на реальные ANSI-коды. Обработка идёт изнутри наружу для
           поддержки вложенных цветов.

        Аргументы:
            message: строка шаблона с переменными.
            var: пользовательские переменные.
            scope: текущий scope вызова.
            ctx: контекст выполнения.
            state: текущее состояние конвейера.
            params: входные параметры действия.

        Возвращает:
            Строка со всеми подстановками, вычисленными iif и ANSI-цветами.

        Исключения:
            LogTemplateError: если переменная не найдена, namespace неизвестен,
                              iif невалиден или обращение к имени с подчёркиванием.
        """
        has_iif = "{iif(" in message

        # Проход 1: подстановка {%...}, маркеры цветов
        resolved = self._substitute_variables(
            message, var, scope, ctx, state, params, has_iif
        )

        # Проход 2: вычисление {iif(...)}
        if has_iif:
            resolved = self._evaluator.process_template(resolved, {})

        # Проход 3: замена цветовых маркеров на ANSI-коды (изнутри наружу)
        return self._apply_color_filters(resolved)
