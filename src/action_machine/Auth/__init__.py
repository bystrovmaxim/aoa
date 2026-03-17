# ActionMachine/Auth/__init__.py
"""
Пакет аутентификации ActionMachine.
Содержит интерфейсы и базовые классы для аутентификации и создания контекста.
"""

from .AuthCoordinator import AuthCoordinator
from .Authenticator import Authenticator
from .CheckRoles import CheckRoles
from .ContextAssembler import ContextAssembler
from .CredentialExtractor import CredentialExtractor

__all__ = [
    "Authenticator",
    "CheckRoles",
    "CredentialExtractor",
    "ContextAssembler",
    "AuthCoordinator",
]
