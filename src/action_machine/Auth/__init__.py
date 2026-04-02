# src/action_machine/auth/__init__.py
"""
Пакет аутентификации ActionMachine.

═══════════════════════════════════════════════════════════════════════════════
НАЗНАЧЕНИЕ
═══════════════════════════════════════════════════════════════════════════════

Содержит все компоненты системы аутентификации и авторизации:

- **check_roles** — декоратор-функция для объявления ролевых ограничений
  на классе действия. Записывает спецификацию ролей в ``cls._role_info``.

- **ROLE_NONE** — строковая константа-маркер «аутентификация не требуется».
  Действие доступно любому пользователю, включая анонимного.

- **ROLE_ANY** — строковая константа-маркер «любая роль подходит».
  Действие требует аутентификации, но конкретная роль не важна.

- **AuthCoordinator** — координатор процесса аутентификации. Объединяет
  три компонента: CredentialExtractor → Authenticator → ContextAssembler.
  Последовательно извлекает учётные данные, проверяет их и собирает
  Context с информацией о пользователе и запросе.

- **NoAuthCoordinator** — провайдер для открытых API. Всегда возвращает
  анонимный Context без пользователя и ролей. Используется для явной
  декларации отсутствия аутентификации.

- **CredentialExtractor** — абстрактный экстрактор учётных данных из
  протокольного запроса (HTTP, MCP и т.д.).

- **Authenticator** — абстрактный аутентификатор. Преобразует учётные
  данные в информацию о пользователе (UserInfo).

- **ContextAssembler** — абстрактный сборщик метаданных запроса
  (trace_id, client_ip, request_path и т.д.).

- **RoleGateHost** — маркерный миксин, разрешающий применение @check_roles.
  Наследуется BaseAction.

═══════════════════════════════════════════════════════════════════════════════
ТИПИЧНОЕ ИСПОЛЬЗОВАНИЕ
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.auth import check_roles, ROLE_NONE, ROLE_ANY

    @check_roles(ROLE_NONE)
    class PingAction(BaseAction[BaseParams, BaseResult]):
        ...

    @check_roles("admin")
    class AdminAction(BaseAction[AdminParams, AdminResult]):
        ...

    @check_roles(["user", "manager"])
    class OrderAction(BaseAction[OrderParams, OrderResult]):
        ...

═══════════════════════════════════════════════════════════════════════════════
АРХИТЕКТУРА АУТЕНТИФИКАЦИИ
═══════════════════════════════════════════════════════════════════════════════

    ┌──────────────────┐     ┌────────────────┐     ┌──────────────────┐
    │ CredentialExtract│ ──▶ │  Authenticator │ ──▶ │ ContextAssembler │
    │ (извлечение      │     │  (проверка     │     │  (сбор метаданных│
    │  учётных данных) │     │   credentials) │     │   запроса)       │
    └──────────────────┘     └────────────────┘     └──────────────────┘
              │                       │                       │
              └───────────────────────┴───────────────────────┘
                                      │
                                      ▼
                              ┌──────────────┐
                              │ AuthCoordinator│
                              │ .process()     │ → Context
                              └──────────────┘
"""

from .auth_coordinator import AuthCoordinator
from .authenticator import Authenticator
from .check_roles import check_roles
from .constants import ROLE_ANY, ROLE_NONE
from .context_assembler import ContextAssembler
from .credential_extractor import CredentialExtractor
from .no_auth_coordinator import NoAuthCoordinator
from .role_gate_host import RoleGateHost

__all__ = [
    "ROLE_ANY",
    "ROLE_NONE",
    "AuthCoordinator",
    "Authenticator",
    "ContextAssembler",
    "CredentialExtractor",
    "NoAuthCoordinator",
    "RoleGateHost",
    "check_roles",
]
