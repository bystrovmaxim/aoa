# Файл: ActionEngine/Exceptions.py
"""
Исключения, используемые в действиях.

Требования:
- Документирование всех методов.
- Текст исколючений писать на русском.
"""
class AuthorizationException(Exception):
    """Ошибка авторизации (недостаточно прав)."""
    pass

class ValidationFieldException(Exception):
    """Ошибка валидации параметра."""
    def __init__(self, message: str, field: str = None):
        super().__init__(message)
        self.field = field

class HandleException(Exception):
    """Ошибка выполнения основной логики действия."""
    pass