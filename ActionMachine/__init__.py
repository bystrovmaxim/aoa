"""
ActionMachine – ядро фреймворка действий.
Экспортирует основные классы для создания действий, валидации, проверки прав и работы с транзакциями.
"""

# Core
from .Core.Exceptions import (
    AuthorizationException,
    ValidationFieldException,
    HandleException,
    TransactionException,
    ConnectionAlreadyOpenError,
    ConnectionNotOpenError,
    TransactionProhibitedError,
)
from .Core.Protocols import ReadableDataProtocol, WritableDataProtocol
from .Core.DataAccessMixins import ReadableMixin, WritableMixin

# ConnectionManagers
from .ResourceManagers.WrapperConnectionManager import WrapperConnectionManager
from .ResourceManagers.PostgresConnectionManager import PostgresConnectionManager

# Checkers
from .Checkers.StringFieldChecker import StringFieldChecker
from .Checkers.IntFieldChecker import IntFieldChecker
from .Checkers.FloatFieldChecker import FloatFieldChecker
from .Checkers.BoolFieldChecker import BoolFieldChecker
from .Checkers.DateFieldChecker import DateFieldChecker
from .Checkers.InstanceOfChecker import InstanceOfChecker

# Context
from .Context.UserInfo import UserInfo
from .Context.RequestInfo import RequestInfo
from .Context.EnvironmentInfo import EnvironmentInfo
from .Context.Context import Context

# Auth
from .Auth.CheckRoles import CheckRoles
from .Auth.Authenticator import Authenticator
from .Auth.CredentialExtractor import CredentialExtractor
from .Auth.ContextAssembler import ContextAssembler
from .Auth.AuthCoordinator import AuthCoordinator

__all__ = [
    # Exceptions
    'AuthorizationException',
    'ValidationFieldException',
    'HandleException',
    'TransactionException',
    'ConnectionAlreadyOpenError',
    'ConnectionNotOpenError',
    'TransactionProhibitedError',

    # Protocols and Mixins
    'ReadableDataProtocol',
    'WritableDataProtocol',
    'ReadableMixin',
    'WritableMixin',

    # ConnectionManagers
    'WrapperConnectionManager',
    'PostgresConnectionManager',

    # Checkers
    'StringFieldChecker',
    'IntFieldChecker',
    'FloatFieldChecker',
    'BoolFieldChecker',
    'DateFieldChecker',
    'InstanceOfChecker',

    # Context
    'UserInfo',
    'RequestInfo',
    'EnvironmentInfo',
    'Context',

    # Auth
    'CheckRoles',
    'Authenticator',
    'CredentialExtractor',
    'ContextAssembler',
    'AuthCoordinator',
]