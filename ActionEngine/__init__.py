# ActionEngine/__init__.py
"""
Пакет ActionEngine – ядро фреймворка действий.
Экспортирует основные классы для создания действий, валидации, проверки прав и работы с транзакциями.
"""

# Базовые действия
from .BaseSimpleAction import BaseSimpleAction
from .BaseTransactionAction import BaseTransactionAction
from .BaseConnectionManager import BaseConnectionManager

# Контекст
from .Context import Context
from .TransactionContext import TransactionContext

# Роли и декораторы
from .CheckRoles import CheckRoles
from .requires_connection_type import requires_connection_type

# Чекеры полей
from .StringFieldChecker import StringFieldChecker
from .IntFieldChecker import IntFieldChecker
from .FloatFieldChecker import FloatFieldChecker
from .BoolFieldChecker import BoolFieldChecker
from .DateFieldChecker import DateFieldChecker

# Исключения
from .Exceptions import (
    AuthorizationException,
    ValidationFieldException,
    HandleException,
    TransactionException,
    ConnectionAlreadyOpenError,
    ConnectionNotOpenError,
)

# Для удобства можно также импортировать базовый чекер (обычно не требуется напрямую)
# from .BaseFieldChecker import BaseFieldChecker