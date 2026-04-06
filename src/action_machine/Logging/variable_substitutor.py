# src/action_machine/logging/variable_substitutor.py
"""
Подстановщик переменных для шаблонов логирования ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

VariableSubstitutor отвечает за:

1. Разрешение переменных {%namespace.dotpath} из пяти источников:
   - var     — словарь пользовательских переменных.
   - state   — текущее состояние конвейера (BaseState, наследник BaseSchema).
   - scope   — LogScope (объект с dict-доступом, не pydantic) [3].
   - context — контекст выполнения (Context, наследник BaseSchema) [2].
   - params  — входные параметры действия (BaseParams, наследник BaseSchema) [2].

2. Двухпроходную подстановку:
   - Проход 1: замена {%namespace.path} на значения.
     Внутри {iif(...)} значения подставляются как литералы
     (строки в кавычках, числа как есть).
   - Проход 2: вычисление {iif(...)} через ExpressionEvaluator [11].

3. Строгую политику ошибок:
   - Переменная не найдена → LogTemplateError.
   - Неизвестный namespace → LogTemplateError.
   - Невалидный iif → LogTemplateError.
   - Обращение к имени с подчёркиванием в любом сегменте пути → LogTemplateError.

4. Цветовые фильтры: синтаксис {%var.amount|red} (вне iif) и цветовые
   функции red('text') (внутри iif). Преобразуются в маркеры, затем
   заменяются на ANSI-коды.

5. Debug-фильтр: синтаксис {%var.obj|debug} выводит форматированную
   интроспекцию объекта (публичные поля и свойства).

6. Маскирование чувствительных данных: если разрешённая переменная
   является свойством с декоратором @sensitive, значение маскируется
   по параметрам декоратора [12].

═══════════════════════════════════════════════════════════════════════════════
ЗАЩИТА ОТ ДОСТУПА К ПРИВАТНЫМ АТРИБУТАМ
═══════════════════════════════════════════════════════════════════════════════

Шаблоны логирования не должны позволять доступ к приватным атрибутам
объектов. Проверка выполняется для КАЖДОГО сегмента dot-path, а не
только для последнего. Это предотвращает обход защиты через
промежуточные приватные сегменты:

    {%context.user._secret}        → LogTemplateError  (последний сегмент)
    {%context._internal.public}    → LogTemplateError  (промежуточный сегмент)
    {%context.__dict__.keys}       → LogTemplateError  (dunder-сегмент)

Проверка применяется только в VariableSubstitutor (шаблоны логирования).
BaseSchema.resolve() [2] вызывается из доверенного кода и не ограничивает
доступ к приватным атрибутам.

═══════════════════════════════════════════════════════════════════════════════
НАВИГАЦИЯ ПО ВЛОЖЕННЫМ ОБЪЕКТАМ
═══════════════════════════════════════════════════════════════════════════════

Навигация по dot-path делегируется единому DotPathNavigator из модуля
core.navigation. Навигатор обеспечивает единообразное поведение для
всех компонентов фреймворка:

    - BaseSchema → __getitem__ (dict-подобный доступ pydantic-модели) [2].
    - LogScope   → __getitem__ (dict-подобный доступ scope логирования) [3].
    - dict       → прямой доступ по ключу.
    - Любой объект → getattr.

VariableSubstitutor использует navigate_with_source(), который
дополнительно возвращает предпоследний объект в цепочке (source)
и имя последнего сегмента пути. Это необходимо для обнаружения
@sensitive-свойств: декоратор @sensitive вешается на property объекта
source, и для его обнаружения нужно знать, на каком объекте и по
какому имени было прочитано финальное значение [12].

═══════════════════════════════════════════════════════════════════════════════
ВНУТРЕННЯЯ АРХИТЕКТУРА РАЗРЕШЕНИЯ ПЕРЕМЕННЫХ
═══════════════════════════════════════════════════════════════════════════════

Разрешение переменной проходит через конвейер из трёх уровней:

1. _resolve_variable_raw(namespace, path, ...) → (raw_value, source, last_segment)
   Выбирает namespace-резольвер и делегирует навигацию DotPathNavigator.

2. _resolve_and_mask(namespace, path, ...) → (raw_value, masked_str, config)
   Общая логика: валидация пути на '_', вызов _resolve_variable_raw,
   проверка _SENTINEL, обнаружение @sensitive, маскирование.
   Единая точка для шагов 1–5, устраняющая дублирование.

3. Финальное форматирование — зависит от контекста вызова:
   - _resolve_variable() → возвращает masked_str (для простых подстановок).
   - _format_variable_for_template() → форматирует с учётом inside_iif
     (литералы для simpleeval) и фильтров (|color, |debug).

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
from action_machine.core.navigation import _SENTINEL, DotPathNavigator
from action_machine.logging.expression_evaluator import ExpressionEvaluator, debug_value
from action_machine.logging.log_scope import LogScope
from action_machine.logging.masking import mask_value

# ---------------------------------------------------------------------------
# Регулярные выражения
# ---------------------------------------------------------------------------

# Формат: {%namespace} или {%namespace.dotpath} с опциональным |color или |debug
_VARIABLE_PATTERN: re.Pattern[str] = re.compile(
    r"\{%([a-zA-Z_][a-zA-Z0-9_]*)\.?([a-zA-Z_][a-zA-Z0-9_.]*)?(?:\|([a-zA-Z_]+))?\}"
)

# Используется для обнаружения блоков iif, чтобы внутри них подставлять
# значения как литералы.
_IIF_BLOCK_PATTERN: re.Pattern[str] = re.compile(r"\{iif\(.*?\)\}")

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

# Паттерн для обработки цветовых маркеров. Захватывает только маркеры
# без вложенных __COLOR( внутри контента, что обеспечивает обработку
# изнутри наружу при многократном применении в цикле.
_COLOR_MARKER_PATTERN: re.Pattern[str] = re.compile(
    r"__COLOR\(([a-zA-Z_]+)\)((?:(?!__COLOR\().)*)__COLOR_END__",
    re.DOTALL,
)

class VariableSubstitutor:
    """
    Подстановщик переменных и вычислитель iif для шаблонов логирования.

    Содержит всю логику:
    - Разрешение переменных из пяти namespace через dispatch-словарь.
    - Навигация по вложенным объектам через dot-path делегируется
      единому DotPathNavigator из core.navigation.
    - Проверка безопасности: каждый сегмент dot-path проверяется на
      префикс '_' до выполнения навигации. Это предотвращает доступ
      к приватным атрибутам объектов через шаблоны логирования.
    - Общая логика разрешения и маскирования вынесена в _resolve_and_mask(),
      устраняя дублирование между _resolve_variable и
      _format_variable_for_template.
    - Форматирование значений как литералов для simpleeval
      (строки в кавычках, числа как есть).
    - Двухпроходная подстановка: сначала {%...}, затем {iif(...)}.
    - Строгая обработка ошибок: подчёркивания → LogTemplateError.
    - Цветовые фильтры через |color (вне iif) и цветовые функции (внутри iif),
      преобразуемые в маркеры и постобрабатываемые в ANSI-коды.
    - Debug-фильтр через |debug, выводящий интроспекцию объекта.
    - Маскирование @sensitive-свойств [12].

    Атрибуты:
        _evaluator: экземпляр ExpressionEvaluator для вычисления iif [11].
        _namespace_resolvers: dispatch-словарь namespace → метод-резольвер.
    """

    def __init__(self) -> None:
        """Инициализирует подстановщик с вычислителем и резольверами."""
        self._evaluator: ExpressionEvaluator = ExpressionEvaluator()
        self._namespace_resolvers: dict[
            str,
            Callable[
                [str, dict[str, Any], LogScope, Context, BaseState, BaseParams],
                tuple[object, object | None, str | None],
            ],
        ] = {
            "var": self._resolve_ns_var,
            "state": self._resolve_ns_state,
            "scope": self._resolve_ns_scope,
            "context": self._resolve_ns_context,
            "params": self._resolve_ns_params,
        }

    # ----------------------------------------------------------------
    # Проверка безопасности dot-path
    # ----------------------------------------------------------------

    @staticmethod
    def _validate_path_segments(namespace: str, path: str) -> None:
        """
        Проверяет, что ни один сегмент dot-path не начинается с подчёркивания.

        Проверяются ВСЕ сегменты пути, а не только последний. Это
        предотвращает обход защиты через промежуточные приватные сегменты:

            {%context._internal.public_key}  → блокируется на '_internal'
            {%context.__dict__.keys}         → блокируется на '__dict__'
            {%context.user._secret}          → блокируется на '_secret'

        Аргументы:
            namespace: имя источника данных (для сообщения об ошибке).
            path: dot-path строка для проверки.

        Исключения:
            LogTemplateError: если любой сегмент начинается с '_'.
        """
        for segment in path.split("."):
            if segment.startswith("_"):
                raise LogTemplateError(
                    f"Access to name starting with underscore is forbidden: "
                    f"'{segment}' in variable {{%{namespace}.{path}}}. "
                    f"Use a public property if output is needed."
                )

    # ----------------------------------------------------------------
    # Навигация по вложенным объектам
    # ----------------------------------------------------------------

    @staticmethod
    def _resolve_path(
        start: object,
        path: str,
    ) -> tuple[object, object | None, str | None]:
        """
        Разрешает dot-path от заданного объекта.

        Делегирует навигацию единому DotPathNavigator. Возвращает
        кортеж (value, source, last_segment), где:
            - value        — найденное значение или _SENTINEL.
            - source       — предпоследний объект в цепочке (нужен
                             для обнаружения @sensitive-свойств) [12].
            - last_segment — имя последнего сегмента пути.

        Аргументы:
            start: корневой объект навигации.
            path: dot-path строка (может быть пустой).

        Возвращает:
            Кортеж (value, source, last_segment).
        """
        if not path:
            return start, None, None
        return DotPathNavigator.navigate_with_source(start, path)

    # ----------------------------------------------------------------
    # Namespace-резольверы
    # ----------------------------------------------------------------

    def _resolve_ns_var(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None, str | None]:
        """Разрешает переменную из словаря var."""
        return self._resolve_path(var, path)

    def _resolve_ns_state(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None, str | None]:
        """Разрешает переменную из BaseState."""
        return self._resolve_path(state, path)

    def _resolve_ns_scope(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None, str | None]:
        """Разрешает переменную из LogScope [3]."""
        return self._resolve_path(scope, path)

    def _resolve_ns_context(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None, str | None]:
        """Разрешает переменную из Context [2]."""
        return self._resolve_path(ctx, path)

    def _resolve_ns_params(
        self, path: str, var: dict[str, Any], scope: LogScope,
        ctx: Context, state: BaseState, params: BaseParams,
    ) -> tuple[object, object | None, str | None]:
        """Разрешает переменную из BaseParams [2]."""
        return self._resolve_path(params, path)

    # ----------------------------------------------------------------
    # Обнаружение и маскирование @sensitive-свойств
    # ----------------------------------------------------------------

    def _get_property_config(self, obj: object, attr_name: str) -> dict[str, Any] | None:
        """
        Проверяет, имеет ли свойство attr_name на объекте obj декоратор @sensitive.

        Обходит MRO класса объекта, ищет property с _sensitive_config на getter [12].

        Аргументы:
            obj: объект-источник (предпоследний в цепочке навигации).
            attr_name: имя свойства для проверки.

        Возвращает:
            dict с конфигурацией маскирования или None если свойство
            не является @sensitive.
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
    ) -> tuple[object, object | None, str | None]:
        """
        Разрешает одну переменную из шаблона — сырое значение,
        объект-источник и имя последнего сегмента.

        Использует dispatch-словарь _namespace_resolvers для выбора
        источника данных по имени namespace.

        Аргументы:
            namespace: имя источника ("var", "state", "scope", "context", "params").
            path: dot-path строка после namespace (может быть None).
            var: словарь пользовательских переменных.
            scope: текущий scope логирования [3].
            ctx: контекст выполнения [2].
            state: текущее состояние конвейера.
            params: входные параметры действия [2].

        Возвращает:
            Кортеж (value, source, last_segment).

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
    # Общая логика разрешения, валидации и маскирования
    # ----------------------------------------------------------------

    def _resolve_and_mask(
        self,
        namespace: str,
        path: str | None,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> tuple[object, str, dict[str, Any] | None]:
        """
        Единая точка разрешения переменной с валидацией и маскированием.

        Выполняет все общие шаги, которые нужны и _resolve_variable,
        и _format_variable_for_template:

            1. Валидация всех сегментов пути на префикс '_'.
            2. Разрешение через _resolve_variable_raw.
            3. Проверка _SENTINEL → LogTemplateError.
            4. Обнаружение @sensitive через _get_property_config [12].
            5. Маскирование через mask_value если config найден [12].

        Аргументы:
            namespace: имя источника данных.
            path: dot-path после namespace.
            var: словарь пользовательских переменных.
            scope: текущий scope логирования [3].
            ctx: контекст выполнения [2].
            state: текущее состояние конвейера.
            params: входные параметры действия [2].

        Возвращает:
            Кортеж (raw_value, masked_str, config):
                raw_value  — сырое значение (для isinstance-проверок в iif).
                masked_str — строковое представление (замаскированное если
                             @sensitive, иначе str(raw_value)).
                config     — sensitive-конфигурация или None.

        Исключения:
            LogTemplateError: если переменная не найдена или любой
                              сегмент пути начинается с подчёркивания.
        """
        if path is not None:
            self._validate_path_segments(namespace, path)

        raw_value, source, last_segment = self._resolve_variable_raw(
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

        if config and config.get('enabled', True):
            masked_str = mask_value(raw_value, config)
        else:
            masked_str = str(raw_value)

        return raw_value, masked_str, config

    # ----------------------------------------------------------------
    # Строковое разрешение (тонкая обёртка над _resolve_and_mask)
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

        Делегирует всю логику _resolve_and_mask и возвращает masked_str.
        Используется на быстром пути (шаблоны без iif).

        Аргументы:
            namespace: имя источника данных.
            path: dot-path после namespace.
            var: словарь пользовательских переменных.
            scope: текущий scope логирования [3].
            ctx: контекст выполнения [2].
            state: текущее состояние конвейера.
            params: входные параметры действия [2].

        Возвращает:
            Строковое представление значения переменной.

        Исключения:
            LogTemplateError: если переменная не найдена или любой
                              сегмент пути начинается с подчёркивания.
        """
        _, masked_str, _ = self._resolve_and_mask(
            namespace, path, var, scope, ctx, state, params
        )
        return masked_str

    # ----------------------------------------------------------------
    # Форматирование значений как литералов для iif
    # ----------------------------------------------------------------

    @staticmethod
    def _quote_if_string(raw_value: object) -> str:
        """
        Форматирует сырое значение как литерал для simpleeval [11].

        Числа и булевы значения возвращаются как строки без кавычек.
        Строки оборачиваются в одинарные кавычки.
        Цветовые маркеры (__COLOR(...)) возвращаются без кавычек,
        чтобы сохранить маркер для последующей обработки.

        Аргументы:
            raw_value: значение для форматирования.

        Возвращает:
            Строковое представление значения как литерала.
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

        Аргументы:
            message: строка шаблона.
            var: словарь пользовательских переменных.
            scope: текущий scope логирования [3].
            ctx: контекст выполнения [2].
            state: текущее состояние конвейера.
            params: входные параметры действия [2].

        Возвращает:
            Строка с подставленными значениями переменных.
        """
        def replacer(match: re.Match[str]) -> str:
            namespace = match.group(1)
            path = match.group(2)
            filter_name = match.group(3)

            if filter_name == "debug":
                raw_value, _, _ = self._resolve_and_mask(
                    namespace, path, var, scope, ctx, state, params
                )
                return debug_value(raw_value)

            _, masked_str, _ = self._resolve_and_mask(
                namespace, path, var, scope, ctx, state, params
            )

            if filter_name:
                return f"__COLOR({filter_name}){masked_str}__COLOR_END__"

            return masked_str

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

        Делегирует разрешение и маскирование _resolve_and_mask.
        Финальное форматирование зависит от inside_iif:
        - Внутри iif: числа и булевы как литералы без кавычек,
          строки в кавычках через _quote_if_string [11].
        - Вне iif: masked_str как есть.

        Аргументы:
            match: объект совпадения regex.
            var: словарь пользовательских переменных.
            scope: текущий scope логирования [3].
            ctx: контекст выполнения [2].
            state: текущее состояние конвейера.
            params: входные параметры действия [2].
            inside_iif: True если переменная находится внутри блока {iif(...)}.

        Возвращает:
            Отформатированное строковое представление значения.
        """
        namespace = match.group(1)
        path = match.group(2)
        filter_name = match.group(3)

        raw_value, masked_str, _ = self._resolve_and_mask(
            namespace, path, var, scope, ctx, state, params
        )

        if inside_iif:
            if isinstance(raw_value, (bool, int, float)):
                formatted = masked_str
            else:
                formatted = self._quote_if_string(masked_str)
        else:
            formatted = masked_str

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

        Аргументы:
            message: строка шаблона с {iif(...)}.
            var: словарь пользовательских переменных.
            scope: текущий scope логирования [3].
            ctx: контекст выполнения [2].
            state: текущее состояние конвейера.
            params: входные параметры действия [2].

        Возвращает:
            Строка с подставленными переменными (iif ещё не вычислены).
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

        Аргументы:
            message: строка шаблона.
            var: словарь пользовательских переменных.
            scope: текущий scope логирования [3].
            ctx: контекст выполнения [2].
            state: текущее состояние конвейера.
            params: входные параметры действия [2].
            has_iif: True если шаблон содержит {iif(...)}.

        Возвращает:
            Строка с подставленными переменными.
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
            color_name: имя цвета.

        Возвращает:
            ANSI escape-последовательность.

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

        Паттерн предкомпилирован на уровне модуля (_COLOR_MARKER_PATTERN),
        что исключает повторную компиляцию regex при каждом вызове.

        Аргументы:
            text: строка с цветовыми маркерами.

        Возвращает:
            Строка с ANSI escape-кодами вместо маркеров.
        """
        while _COLOR_MARKER_PATTERN.search(text):
            def replacer(match: re.Match[str]) -> str:
                color_name = match.group(1)
                content = match.group(2)
                ansi_code = self._resolve_color_name(color_name)
                return f"{ansi_code}{content}{_RESET_CODE}"

            text = _COLOR_MARKER_PATTERN.sub(replacer, text)

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

        2. Вычисление {iif(...)} через ExpressionEvaluator [11]. simpleeval
           получает выражения с уже подставленными литералами и пустой
           словарь имён. Цветовые функции (red('text')) внутри iif
           возвращают маркеры.

        3. Постобработка цветовых маркеров: замена __COLOR(...)...__COLOR_END__
           на реальные ANSI-коды. Обработка идёт изнутри наружу для
           поддержки вложенных цветов.

        Аргументы:
            message: строка шаблона с переменными.
            var: пользовательские переменные.
            scope: текущий scope вызова [3].
            ctx: контекст выполнения [2].
            state: текущее состояние конвейера.
            params: входные параметры действия [2].

        Возвращает:
            Строка со всеми подстановками, вычисленными iif и ANSI-цветами.

        Исключения:
            LogTemplateError: если переменная не найдена, namespace неизвестен,
                              iif невалиден или любой сегмент пути начинается
                              с подчёркивания.
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
