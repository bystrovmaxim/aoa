"""
ActionMachine – ядро фреймворка действий.
Экспортирует основные классы для создания действий, валидации, проверки прав и работы с транзакциями.
"""

# Core
from .Auth.AuthCoordinator import auth_coordinator
from .Auth.Authenticator import authenticator

# Auth
from .Auth.CheckRoles import check_roles
from .Auth.ContextAssembler import context_assembler
from .Auth.CredentialExtractor import credential_extractor
from .Checkers.BoolFieldChecker import BoolFieldChecker
from .Checkers.DateFieldChecker import DateFieldChecker
from .Checkers.FloatFieldChecker import FloatFieldChecker
from .Checkers.InstanceOfChecker import InstanceOfChecker
from .Checkers.IntFieldChecker import IntFieldChecker

# Checkers
from .Checkers.StringFieldChecker import StringFieldChecker
from .Context.Context import Context
from .Context.EnvironmentInfo import environment_info
from .Context.RequestInfo import request_info

# Context
from .Context.UserInfo import user_info
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
    "user_info",
    "request_info",
    "environment_info",
    "Context",
    # Auth
    "check_roles",
    "authenticator",
    "credential_extractor",
    "context_assembler",
    "auth_coordinator",
]
