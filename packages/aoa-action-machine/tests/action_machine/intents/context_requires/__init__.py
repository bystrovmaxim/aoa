# tests/intents/context_requires/__init__.py
"""
Tests for ActionMachine execution context components.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Covers all context pieces passed into the machine when an action runs:

- UserInfo — user identity (user_id, roles).
  Subclass of BaseSchema (frozen, forbid) [1]. Used for role checks in
  ActionProductMachine._check_action_roles().

- RequestInfo — incoming request metadata (trace_id, request_path, client_ip, etc.).
  Subclass of BaseSchema (frozen, forbid). Filled by the adapter or AuthCoordinator.

- RuntimeInfo — execution environment (hostname, service_name, service_version).
  Subclass of BaseSchema (frozen, forbid). Typically set once at app startup.

- Context — root object combining UserInfo, RequestInfo, and RuntimeInfo.
  Subclass of BaseSchema (frozen, forbid), supports resolve across nested components:
  context.resolve("user.roles"), context.resolve("request.trace_id") [2].

All components inherit BaseSchema [2], enabling dict-like access
(keys, values, items, __getitem__, __contains__, get) and resolve() navigation.
"""
