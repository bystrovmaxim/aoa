# ActionMachine/Logging/VariableSubstitutor.py
"""
Подстановщик переменных для шаблонов логирования AOA.

VariableSubstitutor отвечает за:
1. Разрешение переменных {%namespace.dotpath} из пяти источников:
   - var — словарь от разработчика.
   - state — текущее состояние конвейера.
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
...     context=context,
...     state={"total": 1500.0},
...     params=params,
... )
>>> # result == "Загружено 150 задач для agent_1"

Пример с iif (единый синтаксис {%...} везде):

>>> result = substitutor.substitute(
...     message="{iif({%params.amount} > 1000000; '🚨 КРИТИЧЕСКАЯ'; 'Обычная')} транзакция",
...     var={},
...     scope=scope,
...     context=context,
...     state={},
...     params=params,
... )
>>> # Проход 1: {%params.amount} → 1500000.0
>>> # Проход 2: iif(1500000.0 > 1000000; ...) → "🚨 КРИТИЧЕСКАЯ транзакция"
"""

import re
from collections.abc import Callable
from typing import Any

from action_machine.Context.Context import Context
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.Exceptions import LogTemplateError
from action_machine.Logging.ExpressionEvaluator import expression_evaluator
from action_machine.Logging.LogScope import log_scope

# ---------------------------------------------------------------------------
# Регулярные выражения
# ---------------------------------------------------------------------------

# Регулярное выражение для поиска переменных в шаблоне сообщения.
#
# Формат: {%namespace.dotpath}
#
# Группа 1 (namespace): первый сегмент до точки — определяет
# источник данных. Допустимые символы: буквы латиницы, цифры,
# подчёркивание. Первый символ — буква или подчёркивание.
#
# Группа 2 (path): оставшийся путь после первой точки — dot-path
# внутри источника. Может содержать несколько сегментов через точку.
# Допустимые символы в каждом сегменте: буквы, цифры, подчёркивание.
#
# Примеры совпадений:
#   {%var.amount}           → namespace="var",     path="amount"
#   {%context.user.user_id} → namespace="context",  path="user.user_id"
#   {%scope.action}         → namespace="scope",    path="action"
#   {%state.total}          → namespace="state",    path="total"
#
# Символ '%' в начале отличает переменные логера от обычных
# фигурных скобок в Python f-strings и str.format().
_VARIABLE_PATTERN: re.Pattern[str] = re.compile(r"\{%([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_.]*)\}")

# Регулярное выражение для поиска блоков {iif(...)} в шаблоне.
# Используется для определения позиций iif-блоков,
# чтобы внутри них подставлять значения как литералы
# (строки в кавычках, числа как есть).
_IIF_BLOCK_PATTERN: re.Pattern[str] = re.compile(r"\{iif\(.*?\)\}")


class variable_substitutor:
    """
    Подстановщик переменных и вычислитель iif для шаблонов логирования.

    Содержит всю логику:
    - Разрешение переменных из пяти namespace (var, state, scope,
      context, params) через словарь диспетчеризации.
    - Обход вложенных словарей по dot-path.
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
        и словарь диспетчеризации _namespace_resolvers, который
        связывает каждый допустимый namespace со своим методом-
        резолвером.

        Каждый метод-резолвер имеет единую сигнатуру:
            (path, var, scope, context, state, params) -> object

        Добавление нового namespace:
        1. Добавить строку в словарь.
        2. Написать метод _resolve_ns_<name> с той же сигнатурой.
        """
        self._evaluator: expression_evaluator = expression_evaluator()

        # Словарь диспетчеризации: namespace → метод-резолвер.
        self._namespace_resolvers: dict[
            str, Callable[[str, dict[str, Any], log_scope, Context, dict[str, Any], BaseParams], object]
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

        Обходит вложенные словари по цепочке ключей, разделённых
        точкой. Если на любом шаге ключ не найден или текущий объект
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
    # Каждый резолвер отвечает за один namespace и имеет единую сигнатуру:
    #   (path, var, scope, context, state, params) -> object
    #
    # Единая сигнатура позволяет _resolve_variable_raw вызывать любой
    # резолвер одинаково, не зная какой именно namespace обрабатывается.
    # Некоторые резолверы не используют все параметры, но это допустимо.

    def _resolve_ns_var(
        self,
        path: str,
        var: dict[str, Any],
        scope: log_scope,
        context: Context,
        state: dict[str, Any],
        params: BaseParams,
    ) -> object:
        """
        Разрешает переменную из словаря var.

        Словарь var — это произвольные переменные, переданные
        разработчиком при вызове log/emit. Поддерживает вложенные
        словари через dot-path.

        Аргументы:
            path: dot-path внутри var (например, "count" или "data.value").
            var: словарь переменных от разработчика.
            scope: не используется (единая сигнатура).
            context: не используется (единая сигнатура).
            state: не используется (единая сигнатура).
            params: не используется (единая сигнатура).

        Возвращает:
            Найденное значение или None если путь не удалось пройти.
        """
        return self._resolve_from_dict(var, path)

    def _resolve_ns_state(
        self,
        path: str,
        var: dict[str, Any],
        scope: log_scope,
        context: Context,
        state: dict[str, Any],
        params: BaseParams,
    ) -> object:
        """
        Разрешает переменную из словаря state.

        Словарь state — это текущее состояние конвейера аспектов.
        Поддерживает вложенные словари через dot-path.

        Аргументы:
            path: dot-path внутри state (например, "total").
            var: не используется (единая сигнатура).
            scope: не используется (единая сигнатура).
            context: не используется (единая сигнатура).
            state: словарь текущего состояния конвейера.
            params: не используется (единая сигнатура).

        Возвращает:
            Найденное значение или None если путь не удалось пройти.
        """
        return self._resolve_from_dict(state, path)

    def _resolve_ns_scope(
        self,
        path: str,
        var: dict[str, Any],
        scope: log_scope,
        context: Context,
        state: dict[str, Any],
        params: BaseParams,
    ) -> object:
        """
        Разрешает переменную из LogScope.

        LogScope — это обёртка над словарём произвольных ключей,
        описывающая местоположение в конвейере (action, aspect, event).

        Для плоского пути (без точек) используется scope.get(),
        который напрямую обращается к внутреннему словарю.
        Для вложенных путей (с точками) используется _resolve_from_dict
        по копии внутреннего словаря через scope.to_dict().

        Аргументы:
            path: ключ или dot-path внутри scope.
            var: не используется (единая сигнатура).
            scope: скоуп текущего вызова логера.
            context: не используется (единая сигнатура).
            state: не используется (единая сигнатура).
            params: не используется (единая сигнатура).

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
        scope: log_scope,
        context: Context,
        state: dict[str, Any],
        params: BaseParams,
    ) -> object:
        """
        Разрешает переменную из Context через метод resolve.

        Context и его компоненты (UserInfo, RequestInfo, EnvironmentInfo)
        наследуют ReadableMixin и поддерживают метод resolve,
        который обходит вложенные объекты по цепочке ключей.

        Аргументы:
            path: dot-path внутри context (например, "user.user_id").
            var: не используется (единая сигнатура).
            scope: не используется (единая сигнатура).
            context: контекст выполнения.
            state: не используется (единая сигнатура).
            params: не используется (единая сигнатура).

        Возвращает:
            Найденное значение или None если путь не удалось пройти.
        """
        # Context гарантированно наследует ReadableMixin.
        return context.resolve(path)

    def _resolve_ns_params(
        self,
        path: str,
        var: dict[str, Any],
        scope: log_scope,
        context: Context,
        state: dict[str, Any],
        params: BaseParams,
    ) -> object:
        """
        Разрешает переменную из BaseParams через метод resolve.

        BaseParams наследует ReadableMixin и поддерживает метод resolve
        для обхода вложенных объектов по dot-path.

        Аргументы:
            path: dot-path внутри params (например, "amount").
            var: не используется (единая сигнатура).
            scope: не используется (единая сигнатура).
            context: не используется (единая сигнатура).
            state: не используется (единая сигнатура).
            params: входные параметры действия.

        Возвращает:
            Найденное значение или None если путь не удалось пройти.
        """
        # BaseParams гарантированно наследует ReadableMixin.
        return params.resolve(path)

    # ----------------------------------------------------------------
    # Основной метод разрешения переменных (диспетчеризация)
    # ----------------------------------------------------------------

    def _resolve_variable_raw(
        self,
        namespace: str,
        path: str,
        var: dict[str, Any],
        scope: log_scope,
        context: Context,
        state: dict[str, Any],
        params: BaseParams,
    ) -> object:
        """
        Разрешает одну переменную из шаблона — СЫРОЕ значение (не str).

        Использует словарь диспетчеризации _namespace_resolvers для
        определения метода-резолвера по namespace. Если namespace
        не найден — выбрасывает LogTemplateError.

        Аргументы:
            namespace: первый сегмент переменной ("var", "context",
                       "params", "state", "scope").
            path: оставшийся dot-path после namespace.
            var: словарь переменных от разработчика.
            scope: скоуп текущего вызова.
            context: контекст выполнения.
            state: текущее состояние конвейера.
            params: входные параметры действия.

        Возвращает:
            Сырое значение (int, float, str, bool, list, dict и т.д.)
            или None если не найдено.

        Исключения:
            LogTemplateError: если namespace неизвестен.

        Пример:
            >>> substitutor._resolve_variable_raw(
            ...     "var", "count", {"count": 150}, scope, ctx, {}, params
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

        return resolver(path, var, scope, context, state, params)

    # ----------------------------------------------------------------
    # Строковое разрешение с проверкой на None
    # ----------------------------------------------------------------

    def _resolve_variable(
        self,
        namespace: str,
        path: str,
        var: dict[str, Any],
        scope: log_scope,
        context: Context,
        state: dict[str, Any],
        params: BaseParams,
    ) -> str:
        """
        Разрешает одну переменную — строковый результат.

        Обёртка над _resolve_variable_raw, которая преобразует
        сырое значение в строку. Если значение не найдено —
        выбрасывает LogTemplateError.

        Аргументы:
            namespace: первый сегмент переменной.
            path: оставшийся dot-path после namespace.
            var: словарь переменных от разработчика.
            scope: скоуп текущего вызова.
            context: контекст выполнения.
            state: текущее состояние конвейера.
            params: входные параметры действия.

        Возвращает:
            Строковое представление найденного значения.

        Исключения:
            LogTemplateError: если переменная не найдена
                              или namespace неизвестен.

        Пример:
            >>> substitutor._resolve_variable(
            ...     "var", "count", {"count": 150}, scope, ctx, {}, params
            ... )
            '150'
        """
        value = self._resolve_variable_raw(namespace, path, var, scope, context, state, params)

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

        Используется при подстановке {%...} внутри {iif(...)}.
        Числа и bool подставляются как есть (simpleeval понимает
        их как литералы). Строки оборачиваются в одинарные кавычки,
        чтобы simpleeval видел их как строковые литералы,
        а не как имена неопределённых переменных.

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
            "'it\\'s ok'"
        """
        # bool ПЕРЕД int — потому что bool является подклассом int в Python
        if isinstance(raw_value, bool):
            return str(raw_value)  # True / False
        if isinstance(raw_value, (int, float)):
            return str(raw_value)  # 1500.0

        # Строка → экранируем внутренние одинарные кавычки и оборачиваем
        s = str(raw_value).replace("'", "\\'")
        return f"'{s}'"

    # ----------------------------------------------------------------
    # Единственный публичный метод
    # ----------------------------------------------------------------

    def substitute(
        self,
        message: str,
        var: dict[str, Any],
        scope: log_scope,
        context: Context,
        state: dict[str, Any],
        params: BaseParams,
    ) -> str:
        """
        Выполняет подстановку всех переменных и вычисление iif.

        Единственный публичный метод класса. Принимает шаблон
        сообщения и все источники данных, выполняет двухпроходную
        подстановку и возвращает готовую строку.

        Два прохода:
        1. Подстановка {%namespace.dotpath} — ВЕЗДЕ в шаблоне,
           включая внутри {iif(...)}. Внутри iif значения
           подставляются как литералы: строки в кавычках,
           числа и bool как есть.
        2. Вычисление {iif(...)} — через ExpressionEvaluator.
           simpleeval получает выражения с уже подставленными
           литералами и пустой словарь names={}.

        Единый синтаксис {%namespace.path} работает везде:
        - В тексте: {%params.amount} → "1500.0"
        - В iif: {iif({%params.amount} > 1000; 'HIGH'; 'LOW')}
          → {iif(1500.0 > 1000; 'HIGH'; 'LOW')} → "HIGH"

        Строгая политика: если переменная не найдена —
        выбрасывается LogTemplateError.

        Аргументы:
            message: строка шаблона с переменными.
            var: словарь переменных от разработчика.
            scope: скоуп текущего вызова.
            context: контекст выполнения.
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
            ...     {}, scope, ctx, {}, params,
            ... )
            'Сумма: 1500.0'

        Пример с iif:
            >>> substitutor.substitute(
            ...     "{iif({%params.amount} > 1000; 'HIGH'; 'LOW')}",
            ...     {}, scope, ctx, {}, params,
            ... )
            'HIGH'
        """
        has_iif = "{iif(" in message

        # --- Проход 1: подстановка {%...} переменных ---

        if has_iif:
            # Определяем позиции всех {iif(...)} блоков,
            # чтобы внутри них подставлять значения как литералы
            # (строки в кавычках, числа как есть).
            iif_ranges: list[tuple[int, int]] = []
            for m in _IIF_BLOCK_PATTERN.finditer(message):
                iif_ranges.append((m.start(), m.end()))

            def _inside_iif(pos: int) -> bool:
                """Проверяет, находится ли позиция внутри блока iif."""
                for start, end in iif_ranges:
                    if start <= pos < end:
                        return True
                return False

            def replacer(match: re.Match[str]) -> str:
                namespace = match.group(1)
                path = match.group(2)
                raw = self._resolve_variable_raw(namespace, path, var, scope, context, state, params)
                if raw is None:
                    raise LogTemplateError(
                        f"Переменная '{{%{namespace}.{path}}}' не найдена. "
                        f"Проверьте шаблон сообщения и наличие значения "
                        f"в источнике '{namespace}'."
                    )
                if _inside_iif(match.start()):
                    return self._quote_if_string(raw)
                return str(raw)

        else:
            # Быстрый путь: нет iif, не нужна проверка позиций.
            # Простая подстановка {%...} → str(value).
            def replacer(match: re.Match[str]) -> str:
                namespace = match.group(1)
                path = match.group(2)
                return self._resolve_variable(namespace, path, var, scope, context, state, params)

        resolved = _VARIABLE_PATTERN.sub(replacer, message)

        # --- Проход 2: вычисление {iif(...)} выражений ---
        # 98% случаев — нет iif, быстрый выход.
        if not has_iif:
            return resolved

        # simpleeval обработает литералы: 1500000.0 > 1000000
        # Словарь names пуст — все значения уже подставлены
        # как литералы в проходе 1.
        # LogTemplateError из ExpressionEvaluator полетит наверх.
        return self._evaluator.process_template(resolved, {})
