# ActionMachine/Core/Exceptions.py
"""
Исключения, используемые в ActionMachine.
"""


class AuthorizationError(Exception):
    """Ошибка авторизации (недостаточно прав)."""

    pass


class ValidationFieldError(Exception):
    """Ошибка валидации параметра."""

    def __init__(self, message: str, field: str | None = None) -> None:
        """
        Инициализирует исключение.

        :param message: сообщение об ошибке.
        :param field: имя поля, вызвавшего ошибку (опционально).
        """
        super().__init__(message)
        self.field: str | None = field


class HandleError(Exception):
    """Ошибка выполнения основной логики действия."""

    pass


class TransactionError(Exception):
    """Базовое исключение для ошибок, связанных с транзакциями и соединениями."""

    pass


class ConnectionAlreadyOpenError(TransactionError):
    """Соединение уже открыто (попытка открыть повторно)."""

    pass


class ConnectionNotOpenError(TransactionError):
    """Соединение не открыто (попытка выполнить операцию без открытого соединения)."""

    pass


class TransactionProhibitedError(TransactionError):
    """Выбрасывается при попытке управления транзакцией на вложенном уровне."""

    pass


class ConnectionValidationError(TransactionError):
    """
    Несоответствие переданных connections объявленным через @connection.

    Выбрасывается в ActionProductMachine._check_connections() при нарушении
    одного из правил:
    1. Если у действия нет @connection, но передали непустой connections.
    2. Если у действия есть @connection, но connections не передан.
    3. Если ключи в connections не совпадают с объявленными (лишние или недостающие).
    """

    pass


class LogTemplateError(Exception):
    """
    Ошибка в шаблоне логирования.

    Выбрасывается при:
    - Обращении к несуществующей переменной в шаблоне {%namespace.path}.
    - Неизвестном namespace в шаблоне.
    - Синтаксической ошибке в выражении {iif(...)}.
    - Неверном количестве аргументов iif (ожидается 3, разделённых ';').
    - Ошибке вычисления условия или ветки iif.

    Ошибка в шаблоне лога — это баг разработчика, а не пользователя.
    Она должна обнаруживаться немедленно на первом же запуске,
    а не через месяц по странным строкам в логах.

    Это консистентно с философией AOA: логеры падают громко,
    и шаблоны логов тоже должны падать громко.
    """

    pass
