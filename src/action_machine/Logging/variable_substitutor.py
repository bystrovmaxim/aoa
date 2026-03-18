# ActionMachine/Logging/VariableSubstitutor.py
"""
Подстановщик переменных для шаблонов логирования AOA.
VariableSubstitutor отвечает за:
1. Разрешение переменных {%namespace.dotpath} из пяти источников:
   - var — словарь от разработчика.
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
Единственный публичный метод — substitute(). Он принимает шаблон
сообщения и все источники данных, выполняет подстановку и
возвращает готовую строку. LogCoordinator вызывает substitute()
вместо собственной реализации.
Внутренняя реализация использует словарь диспетчеризации
_namespace_resolvers, что позволяет легко добавлять новые
источники данных. Каждый namespace обрабатывается отдельным
приватным методом-резолвером.
Пример использования (внутри LogCoordinator):
>>> substitutor = VariableSubstitutor()
>>> result = substitutor.substitute(
...     message="Загружено {%var.count} задач для {%context.user.user_id}",
...     var={"count": 150},
...     scope=scope,
...     ctx=context,
...     state=state,
...     params=params,
... )
>>> # result == "Загружено 150 задач для agent_1"
Пример с iif (единый синтаксис {%...} везде):
>>> result = substitutor.substitute(
...     message="{iif({%params.amount} > 1000000; '🚨 КРИТИЧЕСКАЯ'; 'Обычная')} транзакция",
...     var={},
...     scope=scope,
...     ctx=context,
...     state=state,
...     params=params,
... )
>>> # Проход 1: {%params.amount} → 1500000.0
>>> # Проход 2: iif(1500000.0 > 1000000; ...) → "🚨 КРИТИЧЕСКАЯ транзакция"
"""
import re
from collections.abc import Callable
from typing import Any
from action_machine.Context.context import Context
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseState import BaseState
from action_machine.Core.Exceptions import LogTemplateError
from action_machine.Logging.expression_evaluator import ExpressionEvaluator
from action_machine.Logging.log_scope import LogScope

# ---------------------------------------------------------------------------
# Регулярные выражения
# ---------------------------------------------------------------------------
# Формат: {%namespace.dotpath}
# Группа 1 (namespace): источник данных (var, state, scope, context, params).
# Группа 2 (path): dot-path внутри источника.
# Примеры:
#   {%var.amount}           → namespace="var",     path="amount"
#   {%context.user.user_id} → namespace="context",  path="user.user_id"
#   {%scope.action}         → namespace="scope",    path="action"
#   {%state.total}          → namespace="state",    path="total"
_VARIABLE_PATTERN: re.Pattern[str] = re.compile(
    r"\{%([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_.]*)\}"
)
# Используется для определения позиций iif-блоков,
# чтобы внутри них подставлять значения как литералы.
_IIF_BLOCK_PATTERN: re.Pattern[str] = re.compile(r"\{iif\(.*?\)\}")


class VariableSubstitutor:
    """
    Подстановщик переменных и вычислитель iif для шаблонов логирования.
    Содержит всю логику:
    - Разрешение переменных из пяти namespace (var, state, scope,
      context, params) через словарь диспетчеризации.
    - Обход вложенных объектов по dot-path.
    - Форматирование значений как литералов для simpleeval
      (строки в кавычках, числа как есть).
    - Двухпроходная подстановка: сначала {%...}, потом {iif(...)}.
    Атрибуты:
        _evaluator: экземпляр ExpressionEvaluator для вычисления iif.
        _namespace_resolvers: словарь диспетчеризации namespace → метод.
    """

    def __init__(self) -> None:
        """
        Создаёт подстановщик переменных.
        Инициализирует ExpressionEvaluator для вычисления iif
        и словарь диспетчеризации _namespace_resolvers.
        Каждый метод-резолвер имеет единую сигнатуру:
            (path, var, scope, ctx, state, params) -> object
        Добавление нового namespace:
        1. Добавить строку в словарь.
        2. Написать метод _resolve_ns_<name> с той же сигнатурой.
        """
        self._evaluator: ExpressionEvaluator = ExpressionEvaluator()
        # Словарь диспетчеризации: namespace → метод-резолвер.
        self._namespace_resolvers: dict[
            str,
            Callable[
                [str, dict[str, Any], LogScope, Context, BaseState, BaseParams],
                object,
            ],
        ] = {
            "var": self._resolve_ns_var,
            "state": self._resolve_ns_state,
            "scope": self._resolve_ns_scope,
            "context": self._resolve_ns_context,
            "params": self._resolve_ns_params,
        }

    # ----------------------------------------------------------------
    # Вспомогательный метод для обхода вложенных словарей
    # ----------------------------------------------------------------
    @staticmethod
    def _resolve_from_dict(source: dict[str, Any], dotpath: str) -> object:
        """
        Разрешает dot-path внутри обычного словаря.
        Если на любом шаге ключ не найден или текущий объект
        не является словарём — возвращает None.
        Аргументы:
            source: словарь для обхода.
            dotpath: строка вида "total" или "nested.key.value".
        Возвращает:
            Найденное значение или None если путь не удалось пройти.
        Пример:
            >>> VariableSubstitutor._resolve_from_dict({"a": {"b": 42}}, "a.b")
            42
            >>> VariableSubstitutor._resolve_from_dict({"a": 1}, "a.b")
            None
        """
        segments = dotpath.split(".")
        current: object = source
        for segment in segments:
            if isinstance(current, dict):
                if segment in current:
                    current = current[segment]
                else:
                    return None
            else:
                return None
        return current

    # ----------------------------------------------------------------
    # Резолверы для каждого namespace
    # ----------------------------------------------------------------
    #
    # Единая сигнатура: (path, var, scope, ctx, state, params) -> object
    # Позволяет _resolve_variable_raw вызывать любой резолвер одинаково.
    # Некоторые резолверы не используют все параметры — это допустимо.

    def _resolve_ns_var(
        self,
        path: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> object:
        """
        Разрешает переменную из словаря var.
        Поддерживает вложенные словари через dot-path.
        Аргументы:
            path: dot-path внутри var (например, "count" или "data.value").
            var: словарь переменных от разработчика.
        Возвращает:
            Найденное значение или None если путь не удалось пройти.
        """
        return self._resolve_from_dict(var, path)

    def _resolve_ns_state(
        self,
        path: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> object:
        """
        Разрешает переменную из BaseState.
        state — текущее состояние конвейера аспектов.
        Поддерживает вложенный доступ через dot-path (через to_dict).
        Аргументы:
            path: dot-path внутри state (например, "total").
            state: текущее состояние конвейера.
        Возвращает:
            Найденное значение или None если путь не удалось пройти.
        """
        return self._resolve_from_dict(state.to_dict(), path)

    def _resolve_ns_scope(
        self,
        path: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> object:
        """
        Разрешает переменную из LogScope.
        Для плоского пути (без точек) используется scope.get().
        Для вложенных путей — _resolve_from_dict по scope.to_dict().
        Аргументы:
            path: ключ или dot-path внутри scope.
            scope: скоуп текущего вызова логера.
        Возвращает:
            Строковое значение ключа или None если не найден.
        """
        if "." not in path:
            return scope.get(path)
        return self._resolve_from_dict(scope.to_dict(), path)

    def _resolve_ns_context(
        self,
        path: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> object:
        """
        Разрешает переменную из Context через метод resolve.
        Context гарантированно наследует ReadableMixin.
        Аргументы:
            path: dot-path внутри context (например, "user.user_id").
            ctx: контекст выполнения.
        Возвращает:
            Найденное значение или None если путь не удалось пройти.
        """
        return ctx.resolve(path)

    def _resolve_ns_params(
        self,
        path: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> object:
        """
        Разрешает переменную из BaseParams через метод resolve.
        BaseParams гарантированно наследует ReadableMixin.
        Аргументы:
            path: dot-path внутри params (например, "amount").
            params: входные параметры действия.
        Возвращает:
            Найденное значение или None если путь не удалось пройти.
        """
        return params.resolve(path)

    # ----------------------------------------------------------------
    # Основной метод разрешения переменных (диспетчеризация)
    # ----------------------------------------------------------------
    def _resolve_variable_raw(
        self,
        namespace: str,
        path: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> object:
        """
        Разрешает одну переменную из шаблона — сырое значение (не str).
        Использует словарь диспетчеризации _namespace_resolvers.
        Если namespace не найден — выбрасывает LogTemplateError.
        Аргументы:
            namespace: первый сегмент переменной ("var", "context",
                       "params", "state", "scope").
            path: оставшийся dot-path после namespace.
            var: словарь переменных от разработчика.
            scope: скоуп текущего вызова.
            ctx: контекст выполнения.
            state: текущее состояние конвейера.
            params: входные параметры действия.
        Возвращает:
            Сырое значение (int, float, str, bool, list, dict и т.д.)
            или None если не найдено.
        Исключения:
            LogTemplateError: если namespace неизвестен.
        Пример:
            >>> substitutor._resolve_variable_raw(
            ...     "var", "count", {"count": 150}, scope, ctx, state, params
            ... )
            150
        """
        resolver = self._namespace_resolvers.get(namespace)
        if resolver is None:
            raise LogTemplateError(
                f"Неизвестный namespace '{namespace}' в шаблоне. "
                f"Допустимые: {', '.join(sorted(self._namespace_resolvers))}. "
                f"Проверьте переменную {{%{namespace}.{path}}}."
            )
        return resolver(path, var, scope, ctx, state, params)

    # ----------------------------------------------------------------
    # Строковое разрешение с проверкой на None
    # ----------------------------------------------------------------
    def _resolve_variable(
        self,
        namespace: str,
        path: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
    ) -> str:
        """
        Разрешает одну переменную — строковый результат.
        Обёртка над _resolve_variable_raw. Если значение не найдено —
        выбрасывает LogTemplateError.
        Аргументы:
            namespace: первый сегмент переменной.
            path: оставшийся dot-path после namespace.
            var: словарь переменных от разработчика.
            scope: скоуп текущего вызова.
            ctx: контекст выполнения.
            state: текущее состояние конвейера.
            params: входные параметры действия.
        Возвращает:
            Строковое представление найденного значения.
        Исключения:
            LogTemplateError: если переменная не найдена
                              или namespace неизвестен.
        Пример:
            >>> substitutor._resolve_variable(
            ...     "var", "count", {"count": 150}, scope, ctx, state, params
            ... )
            '150'
        """
        value = self._resolve_variable_raw(
            namespace, path, var, scope, ctx, state, params
        )
        if value is None:
            raise LogTemplateError(
                f"Переменная '{{%{namespace}.{path}}}' не найдена. "
                f"Проверьте шаблон сообщения и наличие значения "
                f"в источнике '{namespace}'."
            )
        return str(value)

    # ----------------------------------------------------------------
    # Форматирование значений для подстановки внутри iif
    # ----------------------------------------------------------------
    @staticmethod
    def _quote_if_string(raw_value: object) -> str:
        """
        Форматирует сырое значение как литерал для simpleeval.
        Числа и bool подставляются как есть, строки оборачиваются
        в одинарные кавычки.
        Аргументы:
            raw_value: сырое значение переменной.
        Возвращает:
            Строка, пригодная для вставки в выражение simpleeval.
        Примеры:
            >>> VariableSubstitutor._quote_if_string(1500.0)
            '1500.0'
            >>> VariableSubstitutor._quote_if_string(True)
            'True'
            >>> VariableSubstitutor._quote_if_string("agent_1")
            "'agent_1'"
            >>> VariableSubstitutor._quote_if_string("it's ok")
            "\"it\\'s ok\""
        """
        # bool ПЕРЕД int — потому что bool является подклассом int в Python
        if isinstance(raw_value, bool):
            return str(raw_value)
        if isinstance(raw_value, (int, float)):
            return str(raw_value)
        s = str(raw_value).replace("'", "\\'")
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
        Используется когда в шаблоне гарантированно нет {iif(...)}.
        """
        def replacer(match: re.Match[str]) -> str:
            return self._resolve_variable(
                match.group(1), match.group(2),
                var, scope, ctx, state, params,
            )
        return _VARIABLE_PATTERN.sub(replacer, message)

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
        Подстановка с определением позиций iif-блоков.
        Переменные внутри {iif(...)} форматируются как литералы,
        переменные вне iif — как обычные строки.
        """
        iif_ranges = [
            (m.start(), m.end())
            for m in _IIF_BLOCK_PATTERN.finditer(message)
        ]

        def _inside_iif(pos: int) -> bool:
            return any(start <= pos < end for start, end in iif_ranges)

        def replacer(match: re.Match[str]) -> str:
            namespace = match.group(1)
            path = match.group(2)
            raw = self._resolve_variable_raw(
                namespace, path, var, scope, ctx, state, params
            )
            if raw is None:
                raise LogTemplateError(
                    f"Переменная '{{%{namespace}.{path}}}' не найдена. "
                    f"Проверьте шаблон сообщения и наличие значения "
                    f"в источнике '{namespace}'."
                )
            if _inside_iif(match.start()):
                return self._quote_if_string(raw)
            return str(raw)

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
        Если шаблон содержит iif — медленный путь с позиционированием.
        Иначе — быстрый путь без позиционирования.
        """
        if has_iif:
            return self._substitute_with_iif_detection(
                message, var, scope, ctx, state, params
            )
        return self._substitute_simple(message, var, scope, ctx, state, params)

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
        Выполняет подстановку всех переменных и вычисление iif.
        Два прохода:
        1. Подстановка {%namespace.dotpath} — везде в шаблоне,
           включая внутри {iif(...)}. Внутри iif значения
           подставляются как литералы: строки в кавычках,
           числа и bool как есть.
        2. Вычисление {iif(...)} — через ExpressionEvaluator.
           simpleeval получает выражения с уже подставленными
           литералами и пустой словарь names={}.
        Аргументы:
            message: строка шаблона с переменными.
            var: словарь переменных от разработчика.
            scope: скоуп текущего вызова.
            ctx: контекст выполнения.
            state: текущее состояние конвейера.
            params: входные параметры действия.
        Возвращает:
            Строка с выполненными подстановками и вычисленными iif.
        Исключения:
            LogTemplateError: если переменная не найдена,
                              namespace неизвестен или iif невалиден.
        Пример:
            >>> substitutor.substitute(
            ...     "Сумма: {%params.amount}",
            ...     {}, scope, ctx, state, params,
            ... )
            'Сумма: 1500.0'
        Пример с iif:
            >>> substitutor.substitute(
            ...     "{iif({%params.amount} > 1000; 'HIGH'; 'LOW')}",
            ...     {}, scope, ctx, state, params,
            ... )
            'HIGH'
        """
        has_iif = "{iif(" in message
        # --- Проход 1: подстановка {%...} переменных ---
        resolved = self._substitute_variables(
            message, var, scope, ctx, state, params, has_iif
        )
        # --- Проход 2: вычисление {iif(...)} выражений ---
        # 98% случаев — нет iif, быстрый выход.
        if not has_iif:
            return resolved
        # Словарь names пуст — все значения уже подставлены как литералы.
        # LogTemplateError из ExpressionEvaluator полетит наверх.
        return self._evaluator.process_template(resolved, {})