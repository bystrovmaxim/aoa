# ActionMachine/Logging/LogCoordinator.py
"""
Координатор системы логирования AOA.

LogCoordinator — единая шина логирования, к которой подключается
любое количество независимых логеров. Аспекты и плагины отправляют
сообщения в координатор, не зная о конкретных получателях.
Координатор делегирует подстановку переменных классу
VariableSubstitutor и рассылает результат по всем подключённым логерам.

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

Рефакторинг: вся логика подстановки переменных и вычисления iif
вынесена в класс VariableSubstitutor. LogCoordinator стал тонким
координатором: принимает сообщение, делегирует подстановку
VariableSubstitutor.substitute() и рассылает результат логерам.

Пример создания и использования:

>>> from action_machine.Logging.LogCoordinator import LogCoordinator
>>> from action_machine.Logging.ConsoleLogger import ConsoleLogger
>>> from action_machine.Logging.LogScope import LogScope
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

from typing import Any

from action_machine.Context.Context import context
from action_machine.Core.BaseParams import BaseParams
from action_machine.Logging.BaseLogger import base_logger
from action_machine.Logging.LogScope import log_scope
from action_machine.Logging.VariableSubstitutor import variable_substitutor


class log_coordinator:
    """
    Единая шина логирования AOA.

    Принимает сообщения через метод emit, делегирует подстановку
    переменных классу VariableSubstitutor и рассылает результат
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
        _substitutor: экземпляр VariableSubstitutor для подстановки
                      переменных и вычисления iif.
    """

    def __init__(
        self,
        loggers: list[base_logger] | None = None,
    ) -> None:
        """
        Создаёт координатор логирования.

        Принимает опциональный список логеров для начальной регистрации.
        Если список не передан или None — координатор создаётся без
        логеров. Логеры можно добавить позже через add_logger.

        Создаёт экземпляр VariableSubstitutor, который содержит всю
        логику подстановки переменных и вычисления iif. Координатор
        делегирует ему эту работу через метод substitute().

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
        self._loggers: list[base_logger] = list(loggers) if loggers else []

        # Создаём экземпляр VariableSubstitutor, который отвечает за
        # подстановку переменных и вычисление iif.
        self._substitutor: variable_substitutor = variable_substitutor()

    def add_logger(self, logger: base_logger) -> None:
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

    # ----------------------------------------------------------------
    # Основной публичный метод логирования
    # ----------------------------------------------------------------

    async def emit(
        self,
        message: str,
        var: dict[str, Any],
        scope: log_scope,
        context: context,
        state: dict[str, Any],
        params: BaseParams,
        indent: int,
    ) -> None:
        """
        Основной метод логирования — принимает сообщение и рассылает
        его по всем зарегистрированным логерам.

        Выполняет два шага:

        Шаг 1: Подстановка переменных и вычисление iif.
        Делегирует всю работу классу VariableSubstitutor через
        метод substitute(). VariableSubstitutor выполняет:
        - Поиск и замену {%namespace.dotpath} на значения из
          соответствующих источников (var, context, params, state, scope).
        - Внутри {iif(...)} значения подставляются как литералы:
          числа и bool — как есть, строки — в одинарных кавычках.
        - Вычисление {iif(...)} через ExpressionEvaluator.
        Если переменная не найдена — выбрасывается LogTemplateError.
        Если iif невалиден — выбрасывается LogTemplateError.

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
        # Шаг 1: подстановка переменных и вычисление iif.
        # Делегируем всю работу VariableSubstitutor.substitute().
        # VariableSubstitutor содержит логику двухпроходной подстановки
        # и вычисления iif. LogTemplateError из VariableSubstitutor
        # полетит наверх если шаблон невалиден.
        resolved_message = self._substitutor.substitute(message, var, scope, context, state, params)

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
