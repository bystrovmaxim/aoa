################################################################################
# Файл: ActionMachine/Core/Exceptions.py
################################################################################

# ActionMachine/Core/Exceptions.py
"""
Исключения, используемые в ActionMachine.
"""

from typing import Optional


class AuthorizationException(Exception):
    """Ошибка авторизации (недостаточно прав)."""
    pass


class ValidationFieldException(Exception):
    """Ошибка валидации параметра."""

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        """
        Инициализирует исключение.

        :param message: сообщение об ошибке.
        :param field: имя поля, вызвавшего ошибку (опционально).
        """
        super().__init__(message)
        self.field: Optional[str] = field


class HandleException(Exception):
    """Ошибка выполнения основной логики действия."""
    pass


class TransactionException(Exception):
    """Базовое исключение для ошибок, связанных с транзакциями и соединениями."""
    pass


class ConnectionAlreadyOpenError(TransactionException):
    """Соединение уже открыто (попытка открыть повторно)."""
    pass


class ConnectionNotOpenError(TransactionException):
    """Соединение не открыто (попытка выполнить операцию без открытого соединения)."""
    pass


class TransactionProhibitedError(TransactionException):
    """Выбрасывается при попытке управления транзакцией на вложенном уровне."""
    pass


class ConnectionValidationError(TransactionException):
    """
    Несоответствие переданных connections объявленным через @connection.

    Выбрасывается в ActionProductMachine._check_connections() при нарушении
    одного из правил:
    1. Если у действия нет @connection, но передали непустой connections.
    2. Если у действия есть @connection, но connections не передан.
    3. Если ключи в connections не совпадают с объявленными (лишние или недостающие).
    """
    pass

################################################################################