# src/action_machine/Logging/__init__.py
"""
Пакет логирования ActionMachine.

Содержит:

- LogCoordinator — координатор логирования. Принимает список логгеров
  и рассылает каждое сообщение всем подписанным логгерам. Выполняет
  подстановку переменных, маскирование чувствительных данных и применение
  цветовых фильтров перед отправкой.

- ConsoleLogger — логгер, выводящий сообщения в stdout. Поддерживает
  цветной (ANSI) и простой текстовый режимы.

- ActionBoundLogger — обёртка над LogCoordinator, привязанная к конкретному
  действию и аспекту. Создаётся для каждого вызова аспекта, автоматически
  подставляет scope (machine, mode, action, aspect) и nest_level.

- LogScope — frozen-датакласс с полями scope: machine, mode, action, aspect.
  Используется в шаблонах логирования через {%scope.action} и т.д.

- VariableSubstitutor — движок подстановки переменных в шаблонах
  логирования. Поддерживает {%var.name}, {%context.user.roles},
  {%scope.action}, фильтры (|red, |debug), функции (iif, exists, debug).

- ExpressionEvaluator — вычислитель выражений в шаблонах (iif, exists,
  сравнения, арифметика).

- sensitive — декоратор для маскирования чувствительных данных в логах.
  Применяется к property, записывает _sensitive_config в getter.
  MetadataBuilder._collect_sensitive_fields(cls) собирает конфигурации
  в ClassMetadata.sensitive_fields.
"""

from .action_bound_logger import ActionBoundLogger
from .console_logger import ConsoleLogger
from .expression_evaluator import ExpressionEvaluator
from .log_coordinator import LogCoordinator
from .log_scope import LogScope
from .sensitive_decorator import sensitive
from .variable_substitutor import VariableSubstitutor

__all__ = [
    "LogCoordinator",
    "ConsoleLogger",
    "ActionBoundLogger",
    "LogScope",
    "VariableSubstitutor",
    "ExpressionEvaluator",
    "sensitive",
]