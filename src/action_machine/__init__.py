# src/action_machine/__init__.py
"""
ActionMachine – ядро фреймворка действий.
Экспортирует основные классы для создания действий, валидации, проверки прав и работы с транзакциями.

Изменения (этап 1):
- Добавлен экспорт ToolsBox для использования в аспектах.
- Обновлены комментарии.
"""

# Core
from .Auth.auth_coordinator import AuthCoordinator
from .Auth.authenticator import Authenticator

# Auth
from .Auth.check_roles import CheckRoles
from .Auth.context_assembler import ContextAssembler
from .Auth.credential_extractor import CredentialExtractor
from .Checkers.BoolFieldChecker import BoolFieldChecker
from .Checkers.DateFieldChecker import DateFieldChecker
from .Checkers.FloatFieldChecker import FloatFieldChecker
from .Checkers.InstanceOfChecker import InstanceOfChecker
from .Checkers.IntFieldChecker import IntFieldChecker

# Checkers
from .Checkers.StringFieldChecker import StringFieldChecker
from .Context.context import Context
from .Context.request_info import RequestInfo
from .Context.runtime_info import RuntimeInfo

# Context
from .Context.user_info import UserInfo
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
from .ResourceManagers.PostgresConnectionManager import PostgresConnectionManager

# ConnectionManagers
from .ResourceManagers.WrapperConnectionManager import WrapperConnectionManager

__all__ = [
    # Exceptions
    "AuthorizationError",
    "ValidationFieldError",
    "HandleError",
    "TransactionError",
    "ConnectionAlreadyOpenError",
    "ConnectionNotOpenError",
    "TransactionProhibitedError",
    # Protocols and Mixins
    "ReadableDataProtocol",
    "WritableDataProtocol",
    "ReadableMixin",
    "WritableMixin",
    # Tools
    "ToolsBox",
    # ConnectionManagers
    "WrapperConnectionManager",
    "PostgresConnectionManager",
    # Checkers
    "StringFieldChecker",
    "IntFieldChecker",
    "FloatFieldChecker",
    "BoolFieldChecker",
    "DateFieldChecker",
    "InstanceOfChecker",
    # Context
    "UserInfo",
    "RequestInfo",
    "RuntimeInfo",
    "Context",
    # Auth
    "CheckRoles",
    "Authenticator",
    "CredentialExtractor",
    "ContextAssembler",
    "AuthCoordinator",
]