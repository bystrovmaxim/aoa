# src/action_machine/logging/__init__.py
"""
Пакет логирования ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Предоставляет полную подсистему логирования для ActionMachine. Все компоненты
логирования сосредоточены в этом пакете и доступны через единый импорт.

═══════════════════════════════════════════════════════════════════════════════
КОМПОНЕНТЫ
═══════════════════════════════════════════════════════════════════════════════

- LogCoordinator — координатор логирования. Принимает список логгеров
  и рассылает каждое сообщение всем подписанным логгерам. Выполняет
  подстановку переменных, маскирование чувствительных данных и применение
  цветовых фильтров перед отправкой.

- ConsoleLogger — логгер, выводящий сообщения в stdout. Поддерживает
  цветной (ANSI) и простой текстовый режимы.

- ScopedLogger — логгер, привязанный к scope конкретного аспекта.
  Создаётся ActionProductMachine для каждого вызова аспекта, автоматически
  подставляет scope (machine, mode, action, aspect) и nest_level.
  Передаётся в аспекты через ToolsBox.

- LogScope — frozen-датакласс с полями scope: machine, mode, action, aspect.
  Используется в шаблонах логирования через {%scope.action} и т.д.

- VariableSubstitutor — движок подстановки переменных в шаблонах
  логирования. Поддерживает {%var.name}, {%context.user.roles},
  {%scope.action}, фильтры (|red, |debug), функции (iif, exists, debug).

- ExpressionEvaluator — вычислитель выражений в шаблонах (iif, exists,
  сравнения, арифметика). Использует simpleeval для безопасного
  вычисления без доступа к файловой системе и сети.

- sensitive — декоратор для маскирования чувствительных данных в логах.
  Применяется к property, записывает _sensitive_config в getter.
  MetadataBuilder._collect_sensitive_fields(cls) собирает конфигурации
  в ClassMetadata.sensitive_fields.
"""

from .console_logger import ConsoleLogger
from .expression_evaluator import ExpressionEvaluator
from .log_coordinator import LogCoordinator
from .log_scope import LogScope
from .scoped_logger import ScopedLogger
from .sensitive_decorator import sensitive
from .variable_substitutor import VariableSubstitutor

__all__ = [
    "LogCoordinator",
    "ConsoleLogger",
    "ScopedLogger",
    "LogScope",
    "VariableSubstitutor",
    "ExpressionEvaluator",
    "sensitive",
]
