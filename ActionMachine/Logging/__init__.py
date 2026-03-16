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

>>> from ActionMachine.Logging import LogCoordinator, ConsoleLogger, LogScope
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

from .LogCoordinator import LogCoordinator
from .BaseLogger import BaseLogger
from .ConsoleLogger import ConsoleLogger
from .LogScope import LogScope
from .VariableSubstitutor import VariableSubstitutor

__all__ = [
    'LogCoordinator',       # координатор — единая шина логирования
    'BaseLogger',           # абстрактный базовый класс для всех логеров
    'ConsoleLogger',        # логер с выводом в консоль через print
    'LogScope',             # скоуп — обёртка над словарём местоположения в конвейере
    'VariableSubstitutor',  # подстановщик переменных {%...} и вычислитель {iif(...)}
]
