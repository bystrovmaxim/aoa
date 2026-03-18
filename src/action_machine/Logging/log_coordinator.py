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
- {%state.total} — обращается к state по ключу "total".
- {%scope.action} — ищет в scope по ключу "action".
Для объектов с ReadableMixin (Context, UserInfo, RequestInfo,
EnvironmentInfo, BaseParams, BaseResult) используется метод resolve,
который обходит вложенные объекты по цепочке ключей, разделённых
точкой. Для обычных словарей (var) и LogScope используется прямой
доступ по ключам с ручным обходом вложенности.
Единый синтаксис переменных:
Паттерн {%namespace.dotpath} работает ВЕЗДЕ — и в тексте сообщения,
и внутри {iif(...)}. Внутри iif строковые значения автоматически
оборачиваются в кавычки, а числа и bool подставляются как литералы.
Строгая политика ошибок:
Если переменная не найдена — выбрасывается LogTemplateError.
Если выражение iif невалидно — выбрасывается LogTemplateError.
Если namespace неизвестен — выбрасывается LogTemplateError.
Ошибка в шаблоне лога — это баг разработчика, который должен
обнаруживаться немедленно на первом же запуске.
LogCoordinator НЕ подавляет исключения из логеров. Если логер
сломан — исключение летит наверх по стеку.
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
...     ctx=context,
...     state=state,
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
...     ctx=context,
...     state=state,
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
from action_machine.Context.context import Context
from action_machine.Core.BaseParams import BaseParams
from action_machine.Core.BaseState import BaseState
from action_machine.Logging.base_logger import BaseLogger
from action_machine.Logging.log_scope import LogScope
from action_machine.Logging.variable_substitutor import VariableSubstitutor


class LogCoordinator:
    """
    Единая шина логирования AOA.
    Принимает сообщения через метод emit, делегирует подстановку
    переменных классу VariableSubstitutor и рассылает результат
    по всем зарегистрированным логерам.
    Логеры регистрируются при создании координатора через параметр
    loggers, или позже через метод add_logger.
    Координатор не фильтрует сообщения — фильтрация выполняется
    каждым логером самостоятельно в методе match_filters.
    Строгая политика ошибок: любая ошибка в шаблоне немедленно
    выбрасывает LogTemplateError.
    Атрибуты:
        _loggers: список зарегистрированных логеров.
        _substitutor: экземпляр VariableSubstitutor для подстановки
                      переменных и вычисления iif.
    """

    def __init__(
        self,
        loggers: list[BaseLogger] | None = None,
    ) -> None:
        """
        Создаёт координатор логирования.
        Аргументы:
            loggers: список экземпляров BaseLogger для начальной
                     регистрации. None или пустой список допустимы.
        Пример:
            >>> coordinator = LogCoordinator(loggers=[
            ...     ConsoleLogger(use_colors=True),
            ...     ConsoleLogger(filters=[r"Payment.*"]),
            ... ])
            >>> coordinator = LogCoordinator()  # без логеров
        """
        self._loggers: list[BaseLogger] = list(loggers) if loggers else []
        self._substitutor: VariableSubstitutor = VariableSubstitutor()

    def add_logger(self, logger: BaseLogger) -> None:
        """
        Регистрирует новый логер в координаторе.
        Логер добавляется в конец списка — первый зарегистрированный
        вызывается первым.
        Аргументы:
            logger: экземпляр BaseLogger для регистрации.
        Пример:
            >>> coordinator.add_logger(ConsoleLogger())
            >>> coordinator.add_logger(ConsoleLogger(
            ...     filters=[r"Error.*"],
            ...     use_colors=False,
            ... ))
        """
        self._loggers.append(logger)

    async def emit(
        self,
        message: str,
        var: dict[str, Any],
        scope: LogScope,
        ctx: Context,
        state: BaseState,
        params: BaseParams,
        indent: int,
    ) -> None:
        """
        Основной метод логирования — принимает сообщение и рассылает
        его по всем зарегистрированным логерам.
        Выполняет два шага:
        Шаг 1: Подстановка переменных и вычисление iif.
        Делегирует всю работу VariableSubstitutor.substitute().
        Если переменная не найдена или iif невалиден —
        выбрасывается LogTemplateError.
        Шаг 2: Рассылка.
        Вызывает await logger.handle(...) для каждого логера.
        Никакого try/except — любая ошибка летит наверх немедленно.
        Аргументы:
            message: строка шаблона с переменными {%namespace.path}
                     и/или {iif(...)}.
            var: словарь переменных, переданных разработчиком в log.
            scope: скоуп текущего вызова (местоположение в конвейере).
            ctx: контекст выполнения (пользователь, запрос, окружение).
            state: текущее состояние конвейера.
            params: входные параметры действия.
            indent: уровень отступа (для вложенных вызовов).
        Исключения:
            LogTemplateError: при любой ошибке в шаблоне.
        Пример:
            >>> await coordinator.emit(
            ...     message="Загружено {%var.count} задач",
            ...     var={"count": 150},
            ...     scope=LogScope(action="SyncAction", aspect="fetch"),
            ...     ctx=context,
            ...     state=state,
            ...     params=params,
            ...     indent=2,
            ... )
        """
        # Шаг 1: подстановка переменных и вычисление iif.
        # LogTemplateError полетит наверх если шаблон невалиден.
        resolved_message = self._substitutor.substitute(
            message, var, scope, ctx, state, params
        )
        # Шаг 2: рассылка по всем логерам
        for logger in self._loggers:
            await logger.handle(
                scope=scope,
                message=resolved_message,
                var=var,
                ctx=ctx,
                state=state,
                params=params,
                indent=indent,
            )