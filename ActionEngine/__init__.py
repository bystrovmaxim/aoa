# ActionEngine/__init__.py
"""
ActionEngine – ядро фреймворка действий.
Экспортирует основные классы для создания действий, валидации, проверки прав и работы с транзакциями.
"""

# Core
from .Core.BaseSimpleAction import BaseSimpleAction
from .Core.BaseTransactionAction import BaseTransactionAction
from .Core.requires_connection_type import requires_connection_type
from .Core.Exceptions import (
    AuthorizationException,
    ValidationFieldException,
    HandleException,
    TransactionException,
    ConnectionAlreadyOpenError,
    ConnectionNotOpenError,
)

# ConnectionManagers
from .ConnectionManagers.BaseConnectionManager import BaseConnectionManager
from .ConnectionManagers.CsvConnectionManager import CsvConnectionManager
from .ConnectionManagers.PostgresConnectionManager import PostgresConnectionManager

# Checkers
from .Checkers.StringFieldChecker import StringFieldChecker
from .Checkers.IntFieldChecker import IntFieldChecker
from .Checkers.FloatFieldChecker import FloatFieldChecker
from .Checkers.BoolFieldChecker import BoolFieldChecker
from .Checkers.DateFieldChecker import DateFieldChecker
from .Checkers.InstanceOfChecker import InstanceOfChecker

# Context – компоненты и классы
from .Context.UserInfo import UserInfo
from .Context.RequestInfo import RequestInfo
from .Context.EnvironmentInfo import EnvironmentInfo
from .Context.Context import Context
from .Context.TransactionContext import TransactionContext

# Auth – классы аутентификации
from .Auth.CheckRoles import CheckRoles
from .Auth.Authenticator import Authenticator
from .Auth.CredentialExtractor import CredentialExtractor
from .Auth.ContextAssembler import ContextAssembler
from .Auth.AuthCoordinator import AuthCoordinator