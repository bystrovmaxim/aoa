# tests/intents/auth/__init__.py
"""
Tests for ActionMachine authentication and authorization.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers authentication components:

- check_roles — class-level decorator for role constraints. Writes spec to cls._role_info.
  Target must inherit RoleIntent. Valid spec forms: NoneRole, AnyRole, a single BaseRole
  subclass, or a non-empty list of BaseRole subclasses (normalized to a tuple). Strings
  and “roles by name” are not used in @check_roles — only BaseRole types and two engine
  sentinels (SystemRole subclasses).

- NoneRole — sealed sentinel class (not for UserInfo.roles). Used only as @check_roles(NoneRole).
  Meaning: action is open without role checks; RoleChecker allows everyone, including
  anonymous (empty UserInfo.roles). Without explicit @check_roles the machine does not
  assume this.

- AnyRole — sealed sentinel: user must be authenticated in the sense of having at least
  one non-system role (a BaseRole type in UserInfo.roles); the specific role does not matter.

- AuthCoordinator — authentication pipeline. Combines CredentialExtractor → Authenticator
  → ContextAssembler.

- NoAuthCoordinator — provider for public APIs. Always returns anonymous Context with
  UserInfo(user_id=None, roles=()).

Runtime role checks are in tests/runtime/test_machine_roles.py. This package focuses on
@check_roles, coordinators, and related logic.
"""
