# ActionEngine/Auth/__init__.py
"""
Пакет аутентификации ActionEngine.
Содержит интерфейсы и базовые классы для аутентификации и создания контекста.
"""

from .Authenticator import Authenticator
from .CheckRoles import CheckRoles
from .CredentialExtractor import CredentialExtractor
from .ContextAssembler import ContextAssembler
from .AuthCoordinator import AuthCoordinator

__all__ = [
    'Authenticator',
    'CheckRoles',
    'CredentialExtractor',
    'ContextAssembler',
    'AuthCoordinator',
]