"""
ActionMachine – ядро фреймворка действий.
Экспортирует основные классы для создания действий, валидации, проверки прав и работы с транзакциями.
"""

# Core
from .Auth.auth_coordinator import auth_coordinator
from .Auth.authenticator import authenticator

# Auth
from .Auth.check_roles import check_roles
from .Auth.context_assembler import context_assembler
from .Auth.credential_extractor import credential_extractor
from .Checkers.BoolFieldChecker import BoolFieldChecker
from .Checkers.DateFieldChecker import DateFieldChecker
from .Checkers.FloatFieldChecker import FloatFieldChecker
from .Checkers.InstanceOfChecker import InstanceOfChecker
from .Checkers.IntFieldChecker import IntFieldChecker

# Checkers
from .Checkers.StringFieldChecker import StringFieldChecker
from .Context.context import context
from .Context.environment_info import environment_info
from .Context.request_info import request_info

# Context
from .Context.user_info import user_info
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
    "context",
    # Auth
    "check_roles",
    "authenticator",
    "credential_extractor",
    "context_assembler",
    "auth_coordinator",
]
