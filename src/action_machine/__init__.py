"""
ActionMachine – ядро фреймворка действий.
Экспортирует основные классы для создания действий, валидации, проверки прав и работы с транзакциями.
"""

# Core
from .Auth.AuthCoordinator import AuthCoordinator
from .Auth.Authenticator import Authenticator

# Auth
from .Auth.CheckRoles import CheckRoles
from .Auth.ContextAssembler import ContextAssembler
from .Auth.CredentialExtractor import CredentialExtractor
from .Checkers.BoolFieldChecker import BoolFieldChecker
from .Checkers.DateFieldChecker import DateFieldChecker
from .Checkers.FloatFieldChecker import FloatFieldChecker
from .Checkers.InstanceOfChecker import InstanceOfChecker
from .Checkers.IntFieldChecker import IntFieldChecker

# Checkers
from .Checkers.StringFieldChecker import StringFieldChecker
from .Context.Context import Context
from .Context.EnvironmentInfo import EnvironmentInfo
from .Context.RequestInfo import RequestInfo

# Context
from .Context.UserInfo import UserInfo
from .Core.Exceptions import (
    AuthorizationException,
    ConnectionAlreadyOpenError,
    ConnectionNotOpenError,
    HandleException,
    TransactionException,
    TransactionProhibitedError,
    ValidationFieldException,
)
from .Core.Protocols import ReadableDataProtocol, WritableDataProtocol
from .Core.ReadableMixin import ReadableMixin
from .Core.WritableMixin import WritableMixin
from .ResourceManagers.PostgresConnectionManager import PostgresConnectionManager

# ConnectionManagers
from .ResourceManagers.WrapperConnectionManager import WrapperConnectionManager

__all__ = [
    # Exceptions
    "AuthorizationException",
    "ValidationFieldException",
    "HandleException",
    "TransactionException",
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
    "UserInfo",
    "RequestInfo",
    "EnvironmentInfo",
    "Context",
    # Auth
    "CheckRoles",
    "Authenticator",
    "CredentialExtractor",
    "ContextAssembler",
    "AuthCoordinator",
]
