# ActionMachine/Logging/__init__.py
"""
Пакет логирования ActionMachine.

Содержит координатор логирования, базовый абстрактный класс логера,
консольный логер, скоуп — обёртку над словарём переменных,
описывающую местоположение в конвейере выполнения, и подстановщик
переменных, выполняющий замену {%namespace.path} и вычисление {iif(...)}.

Координатор принимает сообщения через метод emit, делегирует
подстановку переменных классу VariableSubstitutor и рассылает
результат по всем зарегистрированным логерам. Каждый логер
самостоятельно решает через match_filters, нужно ли ему
обрабатывать сообщение.

Подстановка переменных работает через паттерн {%namespace.dotpath},
где namespace определяет источник данных: var, context, params,
state, scope. Для объектов с ReadableMixin используется метод
resolve, который обходит вложенные объекты по цепочке ключей,
разделённых точкой. Для обычных словарей используется прямой
доступ по ключам с ручным обходом вложенности.

Никакого подавления исключений — ни в BaseLogger, ни в
LogCoordinator, ни в VariableSubstitutor. Если логер сломан,
система должна упасть громко и немедленно. Разработчик узнает
о проблеме в момент её возникновения, а не через месяц
когда нужны логи которых нет.

Все методы асинхронные — логеры могут выполнять IO-операции
(запись в файл, отправка по сети) без блокировки event loop.

Пример создания и использования:

>>> from action_machine.Logging import LogCoordinator, ConsoleLogger, LogScope
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
"""

from .BaseLogger import base_logger
from .ConsoleLogger import console_logger
from .LogCoordinator import log_coordinator
from .LogScope import log_scope
from .VariableSubstitutor import variable_substitutor

__all__ = [
    "log_coordinator",  # координатор — единая шина логирования
    "base_logger",  # абстрактный базовый класс для всех логеров
    "console_logger",  # логер с выводом в консоль через print
    "log_scope",  # скоуп — обёртка над словарём местоположения в конвейере
    "variable_substitutor",  # подстановщик переменных {%...} и вычислитель {iif(...)}
]
