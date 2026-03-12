from typing import Optional

class AuthorizationException(Exception):
    """Ошибка авторизации (недостаточно прав)."""
    pass

class ValidationFieldException(Exception):
    """Ошибка валидации параметра."""
    def __init__(self, message: str, field: Optional[str] = None) -> None:
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