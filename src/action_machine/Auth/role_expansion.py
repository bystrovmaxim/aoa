# src/action_machine/auth/role_expansion.py
"""
Transitive privilege expansion for ``BaseRole`` types (MRO + ``includes``).

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``expand_role_privileges`` answers: *which role types does holding ``role`` imply?*
It unions every ``BaseRole`` ancestor from the Python MRO with all roles reachable
through the ``includes`` tuple (transitive, cycle-safe). ``RoleChecker`` uses this
set to decide whether a user satisfies a ``@check_roles`` requirement.

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Input must be a concrete or abstract subclass of ``BaseRole`` (typically a
  declared role class or a registry-generated ``*StrRole``).
- The walk is deterministic; ``functools.lru_cache`` memoizes per role **type**
  object (role classes are not mutated after import in normal use).

═══════════════════════════════════════════════════════════════════════════════
DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    User role string "order_manager"
          │
          ▼
    resolve_role_name_to_type()
          │
          ▼
    expand_role_privileges(OrderManagerRole)
          │
          ├── MRO: OrderManagerRole, BaseRole subclasses in MRO
          │
          └── includes stack: OrderCreatorRole → OrderViewerRole → …
          │
          ▼
    required_role in expanded_set ?  → allow / deny

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

``OrderManagerRole`` with ``includes = (OrderCreatorRole,)`` and creator including
viewer yields a frozenset containing manager, creator, viewer, and relevant MRO
types.

Edge case: cyclic ``includes`` (invalid graph) is handled with a **visited** set;
PR-3 ``RoleClassInspector`` should reject cycles at ``build()`` time.

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``resolve_role_name_to_type`` prefers a hand-written ``BaseRole`` subclass whose
  ``name`` matches the string; otherwise it delegates to ``StringRoleRegistry``.
- Duplicate ``name`` values across unrelated role classes: first match in the
  subclass walk wins at resolve time; ``GateCoordinator.build()`` rejects
  duplicate stable names via ``RoleClassInspector``.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Pure privilege expansion + string→type resolution for runtime checks.
CONTRACT: ``expand_role_privileges`` is the single expansion primitive for PR-2.
INVARIANTS: Cycle-safe traversal; cached by role type.
FLOW: RoleChecker → resolve → expand → membership test vs required role.
FAILURES: ``TypeError`` only from invalid inputs to helpers (internal misuse).
EXTENSION POINTS: Acyclic ``includes`` enforced on graph build (structural edges).
AI-CORE-END
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator
from functools import lru_cache

from action_machine.auth.base_role import BaseRole
from action_machine.auth.string_role_registry import StringRoleRegistry


def iter_role_subclasses(root: type[BaseRole] = BaseRole) -> Iterator[type[BaseRole]]:
    """Depth-first iteration over every strict subclass of ``root``."""
    stack: list[type[BaseRole]] = list(root.__subclasses__())
    while stack:
        cls = stack.pop()
        yield cls
        stack.extend(cls.__subclasses__())


def role_class_with_stable_name(name: str) -> type[BaseRole] | None:
    """Return a declared ``BaseRole`` whose ``name`` equals ``name.strip()``, else ``None``."""
    key = name.strip()
    for cls in iter_role_subclasses():
        n = getattr(cls, "name", None)
        if isinstance(n, str) and n == key:
            return cls
    return None


def resolve_role_name_to_type(name: str) -> type[BaseRole]:
    """
    Map a user-facing role string to a ``BaseRole`` type.

    Prefers an application-defined role class with matching ``name``; otherwise
    uses ``StringRoleRegistry`` (may synthesize a ``*StrRole`` class).
    """
    stripped = name.strip()
    found = role_class_with_stable_name(stripped)
    if found is not None:
        return found
    return StringRoleRegistry.resolve(stripped)


def _expand_role_privileges_uncached(role: type[BaseRole]) -> frozenset[type[BaseRole]]:
    acc: set[type[BaseRole]] = set()
    seen: set[type[BaseRole]] = set()
    dq: deque[type[BaseRole]] = deque([role])

    while dq:
        current = dq.popleft()
        if current in seen:
            continue
        seen.add(current)

        for base in current.__mro__:
            if base is BaseRole or base is object:
                continue
            if isinstance(base, type) and issubclass(base, BaseRole):
                acc.add(base)

        for inc in current.includes:
            if inc not in seen:
                dq.append(inc)

    return frozenset(acc)


@lru_cache(maxsize=512)
def expand_role_privileges(role: type[BaseRole]) -> frozenset[type[BaseRole]]:
    """Return the frozen set of role types implied by holding ``role``."""
    return _expand_role_privileges_uncached(role)
