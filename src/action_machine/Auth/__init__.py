# src/action_machine/auth/__init__.py
"""
Пакет аутентификации ActionMachine.

Содержит:
- AuthCoordinator — координатор аутентификации (extractor → authenticator → assembler).
- NoAuthCoordinator — провайдер для открытых API (анонимный Context).
- CredentialExtractor — абстрактный экстрактор учётных данных.
- Authenticator — абстрактный аутентификатор.
- ContextAssembler — абстрактный сборщик метаданных запроса.
- CheckRoles — декоратор ролевых ограничений.
- RoleGateHost — маркерный миксин для @CheckRoles.
"""
