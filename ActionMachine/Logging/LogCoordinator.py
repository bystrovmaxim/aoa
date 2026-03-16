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
точкой [1]. Для обычных словарей (var, state) и LogScope
используется прямой доступ по ключам с ручным обходом вложенности.

Если переменная не найдена на любом шаге — подставляется строка
"<none>" без выброса исключения. Это гарантирует что сломанный
шаблон не уронит бизнес-логику, но при этом проблема будет
заметна в выводе логера.

LogCoordinator НЕ подавляет исключения из логеров. Если логер
сломан — исключение летит наверх по стеку. Разработчик узнает
о проблеме немедленно, а не через месяц когда нужны логи
которых нет [1].

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
"""

import re
from typing import Optional, Any

from ActionMachine.Logging.BaseLogger import BaseLogger
from ActionMachine.Logging.LogScope import LogScope
from ActionMachine.Core.ReadableMixin import ReadableMixin
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

# Маркер, подставляемый вместо переменных, которые не удалось
# разрешить. Заметен в выводе и сигнализирует о проблеме
# без падения системы.
_NONE_MARKER: str = "<none>"


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

    Атрибуты:
        _loggers: список зарегистрированных логеров.
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

    def _resolve_from_dict(self, source: dict[str, Any], dotpath: str) -> object:
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

    def _resolve_variable(
        self,
        namespace: str,
        path: str,
        var: dict[str, Any],
        scope: LogScope,
        context: Context,
        state: dict[str, Any],
        params: BaseParams,
    ) -> str:
        """
        Разрешает одну переменную из шаблона сообщения.

        Определяет источник данных по namespace и вызывает
        соответствующий метод разрешения:
        - "var" и "state" — обычные словари, обход через
          _resolve_from_dict.
        - "scope" — LogScope, доступ через get для плоского пути
          или _resolve_from_dict по to_dict() для вложенных путей.
        - "context" и "params" — объекты с ReadableMixin, используется
          метод resolve для обхода вложенных объектов.

        Если значение не найдено — возвращает строку "<none>".
        Если найдено — возвращает str(value).

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
            Строковое представление найденного значения или "<none>".

        Пример:
            >>> coordinator._resolve_variable(
            ...     "var", "count", {"count": 150}, scope, ctx, {}, params
            ... )
            '150'
            >>> coordinator._resolve_variable(
            ...     "context", "user.user_id", {}, scope, ctx, {}, params
            ... )
            'agent_1'
            >>> coordinator._resolve_variable(
            ...     "var", "nonexistent", {}, scope, ctx, {}, params
            ... )
            '<none>'
        """
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

        # Неизвестный namespace или значение не найдено —
        # value остаётся None (инициализировано в начале метода).

        if value is None:
            return _NONE_MARKER

        return str(value)

    def _substitute_variables(
        self,
        message: str,
        var: dict[str, Any],
        scope: LogScope,
        context: Context,
        state: dict[str, Any],
        params: BaseParams,
    ) -> str:
        """
        Выполняет подстановку всех переменных в шаблоне сообщения.

        Ищет все вхождения паттерна {%namespace.dotpath} в строке
        message и заменяет каждое на разрешённое значение.

        Если в сообщении нет переменных — возвращает его без изменений.
        Если переменная не разрешена — подставляет "<none>".

        Аргументы:
            message: строка шаблона с переменными.
            var: словарь переменных от разработчика.
            scope: скоуп текущего вызова.
            context: контекст выполнения.
            state: текущее состояние конвейера.
            params: входные параметры действия.

        Возвращает:
            Строка с выполненными подстановками.

        Пример:
            >>> coordinator._substitute_variables(
            ...     "User {%context.user.user_id} loaded {%var.count} items",
            ...     var={"count": 42},
            ...     scope=scope,
            ...     context=context,
            ...     state={},
            ...     params=params,
            ... )
            'User agent_1 loaded 42 items'
        """
        def replacer(match: re.Match[str]) -> str:
            """
            Callback для re.sub — разрешает одну переменную.

            Аргументы:
                match: объект совпадения регулярного выражения.
                    Группа 1 — namespace, группа 2 — path.

            Возвращает:
                Разрешённое строковое значение или "<none>".
            """
            namespace = match.group(1)
            path = match.group(2)
            return self._resolve_variable(
                namespace, path, var, scope, context, state, params
            )

        return _VARIABLE_PATTERN.sub(replacer, message)

    async def emit(
        self,
        message: str,
        var: dict[str, Any],
        scope: LogScope,
        context: Context,
        state: dict[str, Any],
        params: BaseParams,
        indent: int,
    ) -> None:
        """
        Основной метод логирования — принимает сообщение и рассылает
        его по всем зарегистрированным логерам.

        Выполняет два шага:

        Шаг 1: Подстановка переменных.
            Ищет в message все вхождения паттерна {%namespace.dotpath}
            и заменяет каждое на значение из соответствующего источника.
            Поддерживаемые namespace: var, context, params, state, scope.
            Если значение не найдено — подставляет "<none>".

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

        Никакого try/except вокруг вызова логеров. Если логер упал —
        исключение летит наверх. Это строгая политика: сломанный
        логер = сломанная система, и мы должны это знать немедленно.

        Аргументы:
            message: строка шаблона с переменными вида
                {%namespace.path}.
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
        """
        # Шаг 1: подстановка переменных в шаблоне сообщения.
        resolved_message = self._substitute_variables(
            message, var, scope, context, state, params
        )

        # Шаг 2: рассылка по всем логерам.
        # Каждый логер самостоятельно решает через match_filters,
        # нужно ли ему обрабатывать это сообщение.
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