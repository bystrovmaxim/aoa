# ActionMachine/Logging/LogCoordinator.py
"""
Координатор системы логирования AOA.

LogCoordinator — единая шина логирования, к которой подключается
любое количество независимых логеров. Аспекты и плагины отправляют
сообщения в координатор, не зная о конкретных получателях.
Координатор выполняет подстановку переменных в шаблоне сообщения
и рассылает результат по всем подключённым логерам.

Подстановка переменных работает через паттерн {%namespace.dotpath},
где namespace определяет источник данных:
- {%var.amount} — ищет в словаре var, переданном разработчиком.
- {%context.user.user_id} — вызывает context.resolve("user.user_id").
- {%params.card_token} — вызывает params.resolve("card_token").
- {%state.total} — ищет в словаре state по ключу "total".
- {%scope.action} — ищет в scope по ключу "action".

Для объектов с ReadableMixin (Context, UserInfo, RequestInfo,
EnvironmentInfo, BaseParams, BaseResult) используется метод resolve,
который обходит вложенные объекты по цепочке ключей, разделённых
точкой. Для обычных словарей (var, state) и LogScope
используется прямой доступ по ключам с ручным обходом вложенности.

Единый синтаксис переменных:
Паттерн {%namespace.dotpath} работает ВЕЗДЕ — и в тексте сообщения,
и внутри {iif(...)}. Внутри iif строковые значения автоматически
оборачиваются в кавычки, а числа и bool подставляются как литералы.
Это позволяет simpleeval корректно вычислять выражения без
необходимости собирать отдельный словарь имён.

Строгая политика ошибок:
Если переменная не найдена — выбрасывается LogTemplateError.
Если выражение iif невалидно — выбрасывается LogTemplateError.
Если namespace неизвестен — выбрасывается LogTemplateError.
Ошибка в шаблоне лога — это баг разработчика, который должен
обнаруживаться немедленно на первом же запуске.

Это консистентно с философией AOA для логеров:
логеры падают громко, и шаблоны тоже должны падать громко.

LogCoordinator НЕ подавляет исключения из логеров. Если логер
сломан — исключение летит наверх по стеку. Разработчик узнает
о проблеме немедленно, а не через месяц когда нужны логи
которых нет.

Все методы асинхронные — координатор и логеры могут выполнять
IO-операции (запись в файл, отправка по сети) без блокировки
event loop.

Пример создания и использования:

>>> from ActionMachine.Logging.LogCoordinator import LogCoordinator
>>> from ActionMachine.Logging.ConsoleLogger import ConsoleLogger
>>> from ActionMachine.Logging.LogScope import LogScope
>>>
>>> coordinator = LogCoordinator(loggers=[
...     ConsoleLogger(use_colors=True),
...     ConsoleLogger(filters=[r"ProcessOrder.*"], use_colors=False),
... ])
>>>
>>> scope = LogScope(action="ProcessOrderAction", aspect="validate")
>>> await coordinator.emit(
...     message="Загружено {%var.count} задач для {%context.user.user_id}",
...     var={"count": 150},
...     scope=scope,
...     context=context,
...     state={"total": 1500.0},
...     params=params,
...     indent=1,
... )

# Результат подстановки: "Загружено 150 задач для agent_1"

# Передаётся в каждый логер через handle.

Пример с iif (единый синтаксис {%...} везде):

>>> await coordinator.emit(
...     message="{iif({%params.amount} > 1000000; '🚨 КРИТИЧЕСКАЯ'; 'Обычная')} транзакция на сумму {%params.amount}",
...     var={},
...     scope=scope,
...     context=context,
...     state={},
...     params=params,
...     indent=0,
... )

# Проход 1: подстановка {%...} → "{iif(1500000.0 > 1000000; '🚨 КРИТИЧЕСКАЯ'; 'Обычная')} транзакция на сумму 1500000.0"
# Проход 2: вычисление iif → "🚨 КРИТИЧЕСКАЯ транзакция на сумму 1500000.0"

Пример ошибки (строгая политика):

>>> await coordinator.emit(
...     message="Missing: {%var.nonexistent}",
...     var={},
...     ...
... )
# LogTemplateError: Переменная 'var.nonexistent' не найдена.
"""

import re
from typing import Optional, Any, Dict

from ActionMachine.Logging.BaseLogger import BaseLogger
from ActionMachine.Logging.LogScope import LogScope
from ActionMachine.Logging.ExpressionEvaluator import ExpressionEvaluator
from ActionMachine.Core.ReadableMixin import ReadableMixin
from ActionMachine.Core.Exceptions import LogTemplateError
from ActionMachine.Context.Context import Context
from ActionMachine.Core.BaseParams import BaseParams


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
_VARIABLE_PATTERN: re.Pattern[str] = re.compile(
    r"\{%([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_.]*)\}"
)


# Регулярное выражение для поиска блоков {iif(...)} в шаблоне.
# Используется для определения позиций iif-блоков,
# чтобы внутри них подставлять значения как литералы
# (строки в кавычках, числа как есть).
_IIF_BLOCK_PATTERN: re.Pattern[str] = re.compile(
    r"\{iif\(.*?\)\}"
)


# Допустимые namespace для переменных в шаблоне.
# Используется для валидации и формирования сообщения об ошибке.
_VALID_NAMESPACES = {"var", "state", "scope", "context", "params"}


class LogCoordinator:
    """
    Единая шина логирования AOA.

    Принимает сообщения через метод emit, выполняет подстановку
    переменных из контекста выполнения и рассылает результат
    по всем зарегистрированным логерам.

    Логеры регистрируются при создании координатора через параметр
    loggers, или позже через метод add_logger.

    Координатор не фильтрует сообщения — фильтрация выполняется
    каждым логером самостоятельно в методе match_filters.

    Подстановка переменных использует единый синтаксис {%namespace.path}
    ВЕЗДЕ — и в тексте, и внутри {iif(...)}. Внутри iif строковые
    значения автоматически оборачиваются в кавычки для корректного
    вычисления simpleeval.

    Строгая политика ошибок: любая ошибка в шаблоне (несуществующая
    переменная, неизвестный namespace, невалидный iif) немедленно
    выбрасывает LogTemplateError. Это консистентно с философией AOA:
    логеры падают громко, и шаблоны тоже.

    Атрибуты:
        _loggers: список зарегистрированных логеров.
        _evaluator: экземпляр ExpressionEvaluator для вычисления iif.
    """

    def __init__(
        self,
        loggers: Optional[list[BaseLogger]] = None,
    ) -> None:
        """
        Создаёт координатор логирования.

        Принимает опциональный список логеров для начальной регистрации.
        Если список не передан или None — координатор создаётся без
        логеров. Логеры можно добавить позже через add_logger.

        Аргументы:
            loggers: список экземпляров BaseLogger для начальной
                регистрации. None или пустой список допустимы —
                координатор просто не будет рассылать сообщения
                пока не будет добавлен хотя бы один логер.

        Пример:
            >>> coordinator = LogCoordinator(loggers=[
            ...     ConsoleLogger(use_colors=True),
            ...     ConsoleLogger(filters=[r"Payment.*"]),
            ... ])
            >>> coordinator = LogCoordinator()  # без логеров
        """
        self._loggers: list[BaseLogger] = list(loggers) if loggers else []
        self._evaluator: ExpressionEvaluator = ExpressionEvaluator()

    def add_logger(self, logger: BaseLogger) -> None:
        """
        Регистрирует новый логер в координаторе.

        Логер добавляется в конец списка. Порядок логеров
        определяет порядок вызова — первый зарегистрированный
        вызывается первым.

        Аргументы:
            logger: экземпляр BaseLogger для регистрации.

        Пример:
            >>> coordinator = LogCoordinator()
            >>> coordinator.add_logger(ConsoleLogger())
            >>> coordinator.add_logger(ConsoleLogger(
            ...     filters=[r"Error.*"],
            ...     use_colors=False,
            ... ))
        """
        self._loggers.append(logger)

    def _resolve_from_dict(self, source: Dict[str, Any], dotpath: str) -> object:
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
            >>> coordinator._resolve_from_dict({"a": {"b": 42}}, "a.b")
            42
            >>> coordinator._resolve_from_dict({"a": 1}, "a.b")
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

    def _resolve_variable_raw(
        self,
        namespace: str,
        path: str,
        var: Dict[str, Any],
        scope: LogScope,
        context: Context,
        state: Dict[str, Any],
        params: BaseParams,
    ) -> object:
        """
        Разрешает одну переменную из шаблона и возвращает СЫРОЕ значение (не str).

        Определяет источник данных по namespace и вызывает
        соответствующий метод разрешения:
        - "var" и "state" — обычные словари, обход через
          _resolve_from_dict.
        - "scope" — LogScope, доступ через get для плоского пути
          или _resolve_from_dict по to_dict() для вложенных путей.
        - "context" и "params" — объекты с ReadableMixin, используется
          метод resolve для обхода вложенных объектов.

        Если namespace неизвестен — выбрасывает LogTemplateError.
        Если значение не найдено — возвращает None (проверка
        на None и выброс исключения выполняется в вызывающем коде).

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
            LogTemplateError: если namespace не входит в допустимый
                набор {var, state, scope, context, params}.

        Пример:
            >>> coordinator._resolve_variable_raw(
            ...     "var", "count", {"count": 150}, scope, ctx, {}, params
            ... )
            150
        """
        if namespace not in _VALID_NAMESPACES:
            raise LogTemplateError(
                f"Неизвестный namespace '{namespace}' в шаблоне. "
                f"Допустимые: {', '.join(sorted(_VALID_NAMESPACES))}. "
                f"Проверьте переменную {{%{namespace}.{path}}}."
            )

        value: object = None

        if namespace == "var":
            value = self._resolve_from_dict(var, path)

        elif namespace == "state":
            value = self._resolve_from_dict(state, path)

        elif namespace == "scope":
            # LogScope поддерживает get для плоского доступа.
            # Для вложенных путей используем _resolve_from_dict
            # по внутреннему словарю scope.to_dict().
            if "." not in path:
                value = scope.get(path)
            else:
                value = self._resolve_from_dict(scope.to_dict(), path)

        elif namespace == "context":
            # Context и его компоненты (UserInfo, RequestInfo,
            # EnvironmentInfo) наследуют ReadableMixin
            # и поддерживают метод resolve.
            if isinstance(context, ReadableMixin):
                value = context.resolve(path)

        elif namespace == "params":
            # BaseParams наследует ReadableMixin.
            if isinstance(params, ReadableMixin):
                value = params.resolve(path)

        return value

    def _resolve_variable(
        self,
        namespace: str,
        path: str,
        var: Dict[str, Any],
        scope: LogScope,
        context: Context,
        state: Dict[str, Any],
        params: BaseParams,
    ) -> str:
        """
        Разрешает одну переменную из шаблона сообщения (строковый результат).

        Обёртка над _resolve_variable_raw, которая преобразует
        сырое значение в строку. Если значение не найдено —
        выбрасывает LogTemplateError.

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
            Строковое представление найденного значения.

        Исключения:
            LogTemplateError: если переменная не найдена или
                namespace неизвестен.

        Пример:
            >>> coordinator._resolve_variable(
            ...     "var", "count", {"count": 150}, scope, ctx, {}, params
            ... )
            '150'
        """
        value = self._resolve_variable_raw(
            namespace, path, var, scope, context, state, params
        )

        if value is None:
            raise LogTemplateError(
                f"Переменная '{{%{namespace}.{path}}}' не найдена. "
                f"Проверьте шаблон сообщения и наличие значения "
                f"в источнике '{namespace}'."
            )

        return str(value)

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
            >>> LogCoordinator._quote_if_string(1500.0)
            '1500.0'
            >>> LogCoordinator._quote_if_string(True)
            'True'
            >>> LogCoordinator._quote_if_string("agent_1")
            "'agent_1'"
            >>> LogCoordinator._quote_if_string("it's ok")
            "'it\\'s ok'"
        """
        # bool ПЕРЕД int — потому что bool является подклассом int в Python
        if isinstance(raw_value, bool):
            return str(raw_value)       # True / False
        if isinstance(raw_value, (int, float)):
            return str(raw_value)       # 1500.0
        # Строка → экранируем внутренние одинарные кавычки и оборачиваем
        s = str(raw_value).replace("'", "\\'")
        return f"'{s}'"

    def _substitute_variables(
        self,
        message: str,
        var: Dict[str, Any],
        scope: LogScope,
        context: Context,
        state: Dict[str, Any],
        params: BaseParams,
    ) -> str:
        """
        Выполняет подстановку всех переменных и вычисление iif.

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
                raw = self._resolve_variable_raw(
                    namespace, path, var, scope, context, state, params
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
        else:
            # Быстрый путь: нет iif, не нужна проверка позиций.
            # Простая подстановка {%...} → str(value).
            # _resolve_variable выбросит LogTemplateError если
            # переменная не найдена.
            def replacer(match: re.Match[str]) -> str:
                namespace = match.group(1)
                path = match.group(2)
                return self._resolve_variable(
                    namespace, path, var, scope, context, state, params
                )

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

    async def emit(
        self,
        message: str,
        var: Dict[str, Any],
        scope: LogScope,
        context: Context,
        state: Dict[str, Any],
        params: BaseParams,
        indent: int,
    ) -> None:
        """
        Основной метод логирования — принимает сообщение и рассылает
        его по всем зарегистрированным логерам.

        Выполняет два шага:

        Шаг 1: Подстановка переменных и вычисление iif.
            Ищет в message все вхождения паттерна {%namespace.dotpath}
            и заменяет каждое на значение из соответствующего источника.
            Затем обрабатывает {iif(...)} конструкции через ExpressionEvaluator.
            Поддерживаемые namespace: var, context, params, state, scope.
            Если значение не найдено — выбрасывается LogTemplateError.

            Внутри {iif(...)} переменные подставляются как литералы:
            числа и bool — как есть, строки — в одинарных кавычках.
            Это позволяет использовать единый синтаксис {%namespace.path}
            и в тексте, и внутри iif.

        Шаг 2: Рассылка.
            В цикле вызывает await logger.handle(...) для каждого
            зарегистрированного логера. Каждый логер получает:
            - scope — скоуп текущего вызова (LogScope).
            - resolved_message — сообщение с выполненными подстановками.
            - var — оригинальный словарь переменных от разработчика.
            - context — контекст выполнения.
            - state — текущее состояние конвейера.
            - params — входные параметры действия.
            - indent — уровень отступа для вложенных вызовов.

        Никакого try/except. Если переменная не найдена —
        LogTemplateError. Если iif невалиден — LogTemplateError.
        Если логер упал — его исключение летит наверх.
        Строгая политика: любая ошибка = немедленное обнаружение.

        Аргументы:
            message: строка шаблона с переменными вида
                {%namespace.path} и/или {iif(...)}.
                Внутри iif переменные указываются в том же формате:
                {iif({%params.amount} > 1000; 'HIGH'; 'LOW')}.
            var: словарь переменных, переданных разработчиком
                при вызове log. Произвольные ключи и значения.
            scope: скоуп текущего вызова — описывает местоположение
                в конвейере (action, aspect, event и т.п.).
            context: контекст выполнения (пользователь, запрос,
                окружение).
            state: текущее состояние конвейера (dict).
            params: входные параметры действия.
            indent: уровень отступа (для вложенных вызовов).
                Передаётся логерам как есть для форматирования
                вывода.

        Исключения:
            LogTemplateError: при любой ошибке в шаблоне
                (несуществующая переменная, неизвестный namespace,
                невалидный iif).

        Пример:
            >>> await coordinator.emit(
            ...     message="Загружено {%var.count} задач",
            ...     var={"count": 150},
            ...     scope=LogScope(action="SyncAction", aspect="fetch"),
            ...     context=context,
            ...     state={"total": 1500},
            ...     params=params,
            ...     indent=2,
            ... )

        Пример с iif (единый синтаксис):
            >>> await coordinator.emit(
            ...     message="{iif({%params.amount} > 1000000; '🚨 КРИТИЧЕСКАЯ'; 'Обычная')} транзакция на сумму {%params.amount}",
            ...     var={},
            ...     scope=scope,
            ...     context=context,
            ...     state={},
            ...     params=params,
            ...     indent=0,
            ... )
        """

        # Шаг 1: подстановка переменных и вычисление iif
        # LogTemplateError полетит наверх если шаблон невалиден.
        resolved_message = self._substitute_variables(
            message, var, scope, context, state, params
        )

        # Шаг 2: рассылка по всем логерам
        for logger in self._loggers:
            await logger.handle(
                scope=scope,
                message=resolved_message,
                var=var,
                context=context,
                state=state,
                params=params,
                indent=indent,
            )