# ActionMachine/Auth/__init__.py
"""
Пакет аутентификации ActionMachine.
Содержит интерфейсы и базовые классы для аутентификации и создания контекста.
"""

from .AuthCoordinator import auth_coordinator
from .Authenticator import authenticator
from .CheckRoles import check_roles
from .ContextAssembler import context_assembler
from .CredentialExtractor import CredentialExtractor

__all__ = [
    "authenticator",
    "check_roles",
    "CredentialExtractor",
    "context_assembler",
    "auth_coordinator",
]
