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
  цветной (ANSI) и простой текстовый режимы. Поддерживает настраиваемые
  отступы на основе уровня вложенности: параметры use_indent (вкл/выкл)
  и indent_size (количество пробелов на уровень).

- ScopedLogger — логгер, привязанный к scope конкретного аспекта или
  плагина. Создаётся автоматически:
  - Для аспектов: ActionProductMachine создаёт ScopedLogger с полями
    scope: machine, mode, action, aspect, nest_level.
  - Для плагинов: PluginRunContext создаёт ScopedLogger с полями
    scope: machine, mode, plugin, action, event, nest_level.
  Передаётся в аспекты через ToolsBox, в обработчики плагинов через
  параметр log (при сигнатуре с 4 параметрами).

- LogScope — объект scope с произвольными полями, задаваемыми через kwargs.
  Поддерживает два набора полей:
  - Для аспектов: machine, mode, action, aspect, nest_level.
  - Для плагинов: machine, mode, plugin, action, event, nest_level.
  Все поля доступны в шаблонах через {%scope.*}. Метод as_dotpath()
  возвращает значения, объединённые точками, для фильтрации.

- VariableSubstitutor — движок подстановки переменных в шаблонах
  логирования. Поддерживает {%var.name}, {%context.user.roles},
  {%scope.action}, {%scope.nest_level}, {%scope.plugin}, {%scope.event},
  фильтры (|red, |debug), функции (iif, exists, debug).

- ExpressionEvaluator — вычислитель выражений в шаблонах (iif, exists,
  сравнения, арифметика). Использует simpleeval для безопасного
  вычисления без доступа к файловой системе и сети.

- sensitive — декоратор для маскирования чувствительных данных в логах.
  Применяется к property, записывает _sensitive_config в getter.
  MetadataBuilder._collect_sensitive_fields(cls) собирает конфигурации
  в ClassMetadata.sensitive_fields.

═══════════════════════════════════════════════════════════════════════════════
ДОСТУП К NEST_LEVEL В ШАБЛОНАХ
═══════════════════════════════════════════════════════════════════════════════

Уровень вложенности вызова действия (nest_level) доступен в шаблонах
логирования через {%scope.nest_level}:

    await box.info("[Уровень {%scope.nest_level}] Обработка платежа")

Значения nest_level:
    0 — корневое действие (вызвано через machine.run()).
    1 — дочернее действие (вызвано через box.run() внутри аспекта).
    2 — действие, вложенное в дочернее, и т.д.

nest_level включается в scope как для аспектов, так и для плагинов.

═══════════════════════════════════════════════════════════════════════════════
ЛОГИРОВАНИЕ В ПЛАГИНАХ
═══════════════════════════════════════════════════════════════════════════════

Обработчики плагинов с сигнатурой (self, state, event, log) получают
ScopedLogger с полями scope: machine, mode, plugin, action, event, nest_level.

    @on("global_finish", ".*")
    async def on_finish(self, state, event, log):
        await log.info(
            "[{%scope.plugin}] Действие {%scope.action} "
            "завершено на уровне {%scope.nest_level}"
        )
        return state

Обработчики со старой сигнатурой (self, state, event) продолжают работать
без изменений — логгер не передаётся.
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
