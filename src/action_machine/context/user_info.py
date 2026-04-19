# src/action_machine/context/user_info.py
"""
UserInfo — identity and role metadata for the caller.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``UserInfo`` is a ``Context`` component that carries caller identity:
``user_id`` and a tuple of role classes (``BaseRole`` subclasses).

It is consumed by role guards (for example, ``@check_roles``) and by aspects
via ``@context_requires``/``ContextView`` for audit and telemetry scenarios.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    AuthCoordinator / NoAuthCoordinator
                   |
                   v
    UserInfo(user_id, roles[BaseRole subclasses])
                   |
                   v
    Context(user=UserInfo)
         |                          |
         +--> role checks           +--> aspects via ContextView
              (@check_roles)             (@context_requires)

    Schema hierarchy:
        BaseSchema(BaseModel)
            └── UserInfo (frozen=True, extra="forbid")

═══════════════════════════════════════════════════════════════════════════════
INVARIANTS
═══════════════════════════════════════════════════════════════════════════════

- Immutable after construction.
- Extra fields are forbidden (``extra="forbid"``).
- ``roles`` contains only ``BaseRole`` subclasses.
- Extension is explicit through inheritance with declared fields:

    class BillingUserInfo(UserInfo):
        billing_plan: str = "free"
        tenant_id: str | None = None

═══════════════════════════════════════════════════════════════════════════════
ANONYMOUS USER
═══════════════════════════════════════════════════════════════════════════════

``UserInfo()`` creates an anonymous principal: ``user_id=None`` and ``roles=()``.
This shape is typically used by ``NoAuthCoordinator`` for public endpoints.

═══════════════════════════════════════════════════════════════════════════════
ASPECT ACCESS MODEL
═══════════════════════════════════════════════════════════════════════════════

Direct UserInfo access from aspects is not provided. Supported path is
``@context_requires`` + ``ContextView``:

    @regular_aspect("Audit")
    @context_requires(Ctx.User.user_id, Ctx.User.roles)
    async def audit_aspect(self, params, state, box, connections, ctx):
        user_id = ctx.get(Ctx.User.user_id)    # → "agent_123"
        roles = ctx.get(Ctx.User.roles)        # → (AdminRole, UserRole)

═══════════════════════════════════════════════════════════════════════════════
DICT-LIKE ACCESS (inherited from BaseSchema)
═══════════════════════════════════════════════════════════════════════════════

    user = UserInfo(user_id="agent_123", roles=(AdminRole,))

    user["user_id"]         # → "agent_123"
    user["roles"]           # → (AdminRole,)
    "user_id" in user       # → True
    user.get("user_id")     # → "agent_123"
    list(user.keys())       # → ["user_id", "roles"]

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    # Authenticated user (roles are BaseRole classes):
    user = UserInfo(user_id="john_doe", roles=(UserRole, ManagerRole))

    # Anonymous user:
    anon = UserInfo()
    anon.user_id    # → None
    anon.roles      # → ()

    # Extension via inheritance:
    class TenantUserInfo(UserInfo):
        tenant_id: str = "default"
        department: str | None = None

    user = TenantUserInfo(
        user_id="john",
        roles=(UserRole,),
        tenant_id="acme",
        department="engineering",
    )

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- ``roles`` validation rejects non-sequences and non-``BaseRole`` subclasses.
- JSON mode serializes roles to role names; runtime mode keeps role classes.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Immutable caller-identity schema inside execution context.
CONTRACT: Provide ``user_id`` and role classes for authorization decisions.
INVARIANTS: Frozen object, forbid-extra policy, role-subclass normalization.
FLOW: auth extraction -> UserInfo assembly -> Context propagation -> consumers.
FAILURES: Validation errors occur on malformed ``roles`` input.
EXTENSION POINTS: Inherit UserInfo for project-specific identity fields.
AI-CORE-END
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field, field_serializer, field_validator

from action_machine.auth.base_role import BaseRole
from action_machine.model.base_schema import BaseSchema


class UserInfo(BaseSchema):
    """
    Immutable caller identity schema used by the execution context.

    AI-CORE-BEGIN
    ROLE: Principal metadata contract for authorization and audit.
    CONTRACT: Store ``user_id`` and a normalized tuple of role classes.
    INVARIANTS: Frozen model, forbid-extra fields, roles are BaseRole subclasses.
    AI-CORE-END
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    user_id: str | None = None
    roles: tuple[type[BaseRole], ...] = Field(default_factory=tuple)

    @field_validator("roles", mode="before")
    @classmethod
    def _coerce_roles(cls, v: Any) -> tuple[type[BaseRole], ...]:
        if v is None:
            return ()
        if isinstance(v, list | tuple):
            items = tuple(v)
        else:
            raise TypeError(
                "UserInfo.roles must be a list or tuple of BaseRole subclasses, "
                f"got {type(v).__name__}: {v!r}."
            )
        for i, x in enumerate(items):
            if not isinstance(x, type) or not issubclass(x, BaseRole):
                raise TypeError(
                    f"UserInfo.roles[{i}] must be a BaseRole subclass, got {x!r}."
                )
        return items

    @field_serializer("roles", when_used="json")
    def _serialize_roles(self, roles: tuple[type[BaseRole], ...]) -> list[str]:
        """
        Serialize role classes into stable wire-safe role names for JSON mode.

        Runtime auth keeps ``roles`` as classes for ``issubclass`` checks; only
        JSON projections convert them to strings.
        """
        return [role.name for role in roles]
