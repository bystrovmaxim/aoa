# ActionMachine/Auth/__init__.py
"""
Пакет аутентификации ActionMachine.
Содержит интерфейсы и базовые классы для аутентификации и создания контекста.
"""

from .auth_coordinator import AuthCoordinator
from .authenticator import Authenticator
from .check_roles import CheckRoles
from .context_assembler import ContextAssembler
from .credential_extractor import CredentialExtractor

__all__ = [
    "Authenticator",
    "CheckRoles",
    "CredentialExtractor",
    "ContextAssembler",
    "AuthCoordinator",
]
