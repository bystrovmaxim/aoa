# ActionMachine/Auth/__init__.py
"""
Пакет аутентификации ActionMachine.
Содержит интерфейсы и базовые классы для аутентификации и создания контекста.
"""

from .auth_coordinator import auth_coordinator
from .authenticator import authenticator
from .check_roles import check_roles
from .context_assembler import context_assembler
from .credential_extractor import credential_extractor

__all__ = [
    "authenticator",
    "check_roles",
    "credential_extractor",
    "context_assembler",
    "auth_coordinator",
]
