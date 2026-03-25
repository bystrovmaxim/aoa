"""
ActionMachine – ядро фреймворка действий.

Экспортирует основные классы для создания действий, валидации, проверки прав,
работы с транзакциями и управления компонентами через шлюзы (Gates).

Все метаданные действий и плагинов теперь хранятся в шлюзах:
- RoleGate – для ролевой спецификации
- DependencyGate – для зависимостей
- CheckerGate – для чекеров полей
- OnGate – для подписок плагинов
- AspectGate – для аспектов (реализован отдельно)

Старые атрибуты (_role_spec, _dependencies, _field_checkers, _result_checkers,
_plugin_hooks) заменены на шлюзы и больше не используются в ядре.
"""

# Core
from .Core.BaseAction import BaseAction
from .Core.BaseActionMachine import BaseActionMachine
from .Core.BaseParams import BaseParams
from .Core.BaseResult import BaseResult
from .Core.BaseState import BaseState
from .Core.Exceptions import (
    AuthorizationError,
    ConnectionAlreadyOpenError,
    ConnectionNotOpenError,
    HandleError,
    TransactionError,
    TransactionProhibitedError,
    ValidationFieldError,
)
from .Core.Protocols import ReadableDataProtocol, WritableDataProtocol
from .Core.ReadableMixin import ReadableMixin
from .Core.ToolsBox import ToolsBox
from .Core.WritableMixin import WritableMixin
from .Core.ActionProductMachine import ActionProductMachine
from .Core.ActionTestMachine import ActionTestMachine
from .Core.MockAction import MockAction

# Aspects
from .aspects.regular_aspect import regular_aspect
from .aspects.summary_aspect import summary_aspect
from .aspects.aspect_gate import AspectGate
from .aspects.aspect_gate_host import AspectGateHost

# Auth
from .Auth.auth_coordinator import AuthCoordinator
from .Auth.authenticator import Authenticator
from .Auth.check_roles import CheckRoles
from .Auth.context_assembler import ContextAssembler
from .Auth.credential_extractor import CredentialExtractor
from .Auth.role_gate import RoleGate, RoleInfo
from .Auth.role_gate_host import RoleGateHost

# Checkers
from .Checkers.BaseFieldChecker import BaseFieldChecker
from .Checkers.BoolFieldChecker import BoolFieldChecker
from .Checkers.DateFieldChecker import DateFieldChecker
from .Checkers.FloatFieldChecker import FloatFieldChecker
from .Checkers.InstanceOfChecker import InstanceOfChecker
from .Checkers.IntFieldChecker import IntFieldChecker
from .Checkers.StringFieldChecker import StringFieldChecker
from .Checkers.checker_gate import CheckerGate
from .Checkers.checker_gate_host import CheckerGateHost

# Context
from .Context.context import Context
from .Context.request_info import RequestInfo
from .Context.runtime_info import RuntimeInfo
from .Context.user_info import UserInfo

# Dependencies
from .dependencies.dependency_gate import DependencyGate, DependencyInfo
from .dependencies.dependency_gate_host import DependencyGateHost
from .dependencies.dependency_factory import DependencyFactory
from .dependencies.depends import depends

# Logging
from .Logging.action_bound_logger import ActionBoundLogger
from .Logging.base_logger import BaseLogger
from .Logging.console_logger import ConsoleLogger
from .Logging.log_coordinator import LogCoordinator
from .Logging.log_scope import LogScope
from .Logging.variable_substitutor import VariableSubstitutor

# Plugins
from .Plugins.Decorators import on
from .Plugins.Plugin import Plugin
from .Plugins.PluginCoordinator import PluginCoordinator
from .Plugins.PluginEvent import PluginEvent
from .Plugins.on_gate import OnGate, Subscription
from .Plugins.on_gate_host import OnGateHost

# Resource Managers
from .ResourceManagers.BaseResourceManager import BaseResourceManager
from .ResourceManagers.IConnectionManager import IConnectionManager
from .ResourceManagers.PostgresConnectionManager import PostgresConnectionManager
from .ResourceManagers.WrapperConnectionManager import WrapperConnectionManager
from .ResourceManagers.Connections import Connections

__all__ = [
    # Core
    "BaseAction",
    "BaseActionMachine",
    "BaseParams",
    "BaseResult",
    "BaseState",
    "AuthorizationError",
    "ValidationFieldError",
    "HandleError",
    "TransactionError",
    "ConnectionAlreadyOpenError",
    "ConnectionNotOpenError",
    "TransactionProhibitedError",
    "ReadableDataProtocol",
    "WritableDataProtocol",
    "ReadableMixin",
    "ToolsBox",
    "WritableMixin",
    "ActionProductMachine",
    "ActionTestMachine",
    "MockAction",
    # Aspects
    "regular_aspect",
    "summary_aspect",
    "AspectGate",
    "AspectGateHost",
    # Auth
    "AuthCoordinator",
    "Authenticator",
    "CheckRoles",
    "ContextAssembler",
    "CredentialExtractor",
    "RoleGate",
    "RoleInfo",
    "RoleGateHost",
    # Checkers
    "BaseFieldChecker",
    "BoolFieldChecker",
    "DateFieldChecker",
    "FloatFieldChecker",
    "InstanceOfChecker",
    "IntFieldChecker",
    "StringFieldChecker",
    "CheckerGate",
    "CheckerGateHost",
    # Context
    "UserInfo",
    "RequestInfo",
    "RuntimeInfo",
    "Context",
    # Dependencies
    "DependencyGate",
    "DependencyInfo",
    "DependencyGateHost",
    "DependencyFactory",
    "depends",
    # Logging
    "ActionBoundLogger",
    "BaseLogger",
    "ConsoleLogger",
    "LogCoordinator",
    "LogScope",
    "VariableSubstitutor",
    # Plugins
    "on",
    "Plugin",
    "PluginCoordinator",
    "PluginEvent",
    "OnGate",
    "Subscription",
    "OnGateHost",
    # Resource Managers
    "BaseResourceManager",
    "IConnectionManager",
    "PostgresConnectionManager",
    "WrapperConnectionManager",
    "Connections",
]