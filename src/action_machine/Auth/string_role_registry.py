# src/action_machine/auth/string_role_registry.py
"""
Registry that materializes string role identifiers as ``BaseRole`` subclasses.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Maps ad hoc user role **tokens** (e.g. from JWT claims) to concrete ``BaseRole``
types when no declared role class with a matching ``name`` exists
(``resolve_role_name_to_type``). Each distinct key maps to one cached synthetic
class per process. ``@check_roles`` does **not** accept strings; pass real role
types on actions.
types on actions.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Keys are normalized with ``strip()`` and lowercased for the stable ``name``
  ``ClassVar`` on generated classes.
- Generated classes inherit ``BaseRole``, carry ``@role_mode(ALIVE)``, and use
  a synthetic type name ending with ``Role`` (``NamingSuffixError``-safe).

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::
    resolve_role_name_to_type("manager")  # user token
         │
         ▼
    StringRoleRegistry.resolve("manager")  # if no declared role.name match
    StringRoleRegistry.resolve("manager")
         │
         ├── cache hit → existing type
         │
         └── miss → type(...) + role_mode(ALIVE) → store → return type

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    AdminRole = StringRoleRegistry.resolve("admin")
    assert AdminRole.name == "admin"
    assert issubclass(AdminRole, BaseRole)

Edge case: whitespace-only key → ``ValueError``.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Descriptions are generic template text; hand-written role classes should be
  preferred for documentation-rich policies.
- This registry is **not** a security boundary; it only normalizes declarations.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Adapter from legacy string specs to typed ``BaseRole`` classes.
CONTRACT: ``resolve(str) -> type[BaseRole]``; idempotent cache per key.
INVARIANTS: Lowercase ``name``; ALIVE mode; valid ``*Role`` synthetic names.
FLOW: ``check_roles`` string branch → resolve → tuple or single type in spec.
FAILURES: ValueError on empty key; TypeError from ``BaseRole`` if violated.
EXTENSION POINTS: Replace string usage with explicit role classes in app code.
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from threading import Lock

from action_machine.auth.base_role import BaseRole
from action_machine.auth.role_mode import RoleMode
from action_machine.auth.role_mode_decorator import role_mode

_LOCK = Lock()
_CACHE: dict[str, type[BaseRole]] = {}


def _synthetic_type_name(key: str) -> str:
    safe = "".join(c if c.isalnum() else "_" for c in key.strip())
    parts = [p for p in safe.split("_") if p]
    pascal = "".join(p.capitalize() for p in parts) if parts else "X"
    return f"{pascal}StrRole"


class StringRoleRegistry:
    """
    Maps normalized string keys to shared ``BaseRole`` subclasses (cached).

    Intended for ``@check_roles`` normalization, not for end-user extension.
    """

    @classmethod
    def resolve(cls, key: str) -> type[BaseRole]:
        """Return the ``BaseRole`` type for ``key`` (create and cache on first use)."""
        normalized = key.strip().lower()
        if not normalized:
            raise ValueError("StringRoleRegistry.resolve: key cannot be empty.")

        with _LOCK:
            cached = _CACHE.get(normalized)
            if cached is not None:
                return cached

            type_name = _synthetic_type_name(normalized)
            new_cls = type(
                type_name,
                (BaseRole,),
                {
                    "name": normalized,
                    "description": f"Registry-generated role for `{normalized}`.",
                    "includes": (),
                },
            )
            decorated = role_mode(RoleMode.ALIVE)(new_cls)
            _CACHE[normalized] = decorated
            return decorated

    @classmethod
    def clear_cache_for_tests(cls) -> None:
        """Drop cached synthetic classes (test isolation only)."""
        with _LOCK:
            _CACHE.clear()
