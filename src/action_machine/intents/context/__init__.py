# src/action_machine/intents/context/__init__.py
"""
ActionMachine execution context package.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Contains the full action-execution context system:

- **Context** — action execution context. Holds user info (``UserInfo``),
  request info (``RequestInfo``), and runtime info (``RuntimeInfo``).
  Passed to runtime ``run()`` and used for role checks and logging.

- **UserInfo** — authenticated user metadata (``user_id``, ``roles``).

- **RequestInfo** — inbound request metadata (trace_id, client_ip,
  request_path, protocol, etc.).

- **RuntimeInfo** — runtime environment metadata (hostname, service_name,
  service_version, etc.).

- **Ctx** — nested dot-path constants used by ``@context_requires``.
  Every constant maps to a real field:
  ``Ctx.User.user_id == "user.user_id"``,
  ``Ctx.Request.trace_id == "request.trace_id"``, etc.

- **ContextView** — frozen object with restricted access to context fields.
  Created by runtime for aspects using ``@context_requires``.
  Public method ``get(key)`` ensures the key is allowed by declaration and
  delegates to ``context.resolve(key)``. Accessing undeclared keys raises
  ``ContextAccessError``.

- **context_requires** — method-level decorator declaring context fields
  required by an aspect or error handler. Writes frozenset of keys to
  ``func._required_context_keys``. Presence of this decorator extends expected
  method signature with ``ctx: ContextView`` parameter.

- **ContextRequiresIntent** — marker mixin declaring support for
  ``@context_requires``. Inherited by ``BaseAction``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

All context components inherit ``BaseSchema``, which provides:
- Dict-like field access (``obj["key"]``, ``obj.keys()``, ...).
- Dot-path navigation (``context.resolve("user.user_id")``).
- Immutability (``frozen=True`` on all components).
- Forbidden extra fields (``extra="forbid"``); extension is explicit via
  inheritance with declared fields.
- Serialization via ``model_dump()`` for logs/adapters.

    BaseSchema(BaseModel)
        ├── UserInfo       — frozen, forbid
        ├── RequestInfo    — frozen, forbid
        ├── RuntimeInfo    — frozen, forbid
        └── Context        — frozen, forbid
                ├── user: UserInfo
                ├── request: RequestInfo
                └── runtime: RuntimeInfo

═══════════════════════════════════════════════════════════════════════════════
CONTROLLED CONTEXT ACCESS
═══════════════════════════════════════════════════════════════════════════════

``ToolsBox`` does not expose ``Context``; aspects cannot access context through
box. The only supported way is ``ctx: ContextView`` provided by runtime when
``@context_requires`` is declared.

Without ``@context_requires``, aspects have no context access.
Most aspects (amount validation, payment handling) do not need context and
work only with params, state, box, and connections.

Flow:
    1. Aspect declares: ``@context_requires(Ctx.User.user_id)``.
    2. Inspector stores: ``aspect_snapshot.context_keys = frozenset({"user.user_id"})``.
    3. Runtime creates: ``ContextView(context, context_keys)``.
    4. Aspect reads: ``ctx.get(Ctx.User.user_id)``.
    5. Undeclared key access: ``ctx.get(Ctx.User.roles)`` -> ``ContextAccessError``.

═══════════════════════════════════════════════════════════════════════════════
VARIABLE ASPECT SIGNATURES
═══════════════════════════════════════════════════════════════════════════════

Presence of ``@context_requires`` changes expected method signature:

    Aspects (``@regular_aspect``, ``@summary_aspect``):
        Without ``@context_requires`` -> (self, params, state, box, connections)     — 5 parameters
        With ``@context_requires``    -> (self, params, state, box, connections, ctx) — 6 parameters

    Error handlers (``@on_error``):
        Without ``@context_requires`` -> (self, params, state, box, connections, error)      — 6 parameters
        With ``@context_requires``    -> (self, params, state, box, connections, error, ctx) — 7 parameters

═══════════════════════════════════════════════════════════════════════════════
EXTENDING CONTEXT COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

``UserInfo``, ``RequestInfo``, and ``RuntimeInfo`` are extended via inheritance
with explicitly declared fields. ``Ctx`` constants cover standard fields.
For custom fields, use raw strings:

    @context_requires(Ctx.User.user_id, "user.billing_plan")

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

    from action_machine.context import Ctx, ContextView
    from action_machine.intents.context import context_requires

    @regular_aspect("Audit")
    @context_requires(Ctx.User.user_id, Ctx.Request.client_ip)
    async def audit_aspect(self, params, state, box, connections, ctx):
        user = ctx.get(Ctx.User.user_id)
        ip = ctx.get(Ctx.Request.client_ip)
        return {"audited_by": user}

    # Aspect without context — standard signature:
    @regular_aspect("Calculate")
    async def calculate_aspect(self, params, state, box, connections):
        return {"total": params.amount * 1.2}

═══════════════════════════════════════════════════════════════════════════════
ERRORS / LIMITATIONS
═══════════════════════════════════════════════════════════════════════════════

- Accessing undeclared context keys through ``ContextView`` raises
  ``ContextAccessError``.
- Signature mismatch between context declaration and method parameters is
  validated by decorator/inspector contracts.

═══════════════════════════════════════════════════════════════════════════════
AI-CORE-BEGIN
═══════════════════════════════════════════════════════════════════════════════
ROLE: Public context package API surface.
CONTRACT: Export immutable context models, context access controls, and declaration decorators.
INVARIANTS: Controlled access via ContextView and explicit context_requires declarations.
FLOW: auth/context assembly -> facet declarations -> runtime ContextView access.
FAILURES: ContextAccessError for undeclared key access.
EXTENSION POINTS: Schema inheritance and custom dot-path keys.
AI-CORE-END
"""

from action_machine.context.context import Context
from action_machine.context.context_view import ContextView
from action_machine.context.ctx_constants import Ctx
from action_machine.context.request_info import RequestInfo
from action_machine.context.runtime_info import RuntimeInfo
from action_machine.context.user_info import UserInfo
from action_machine.intents.context.context_requires_decorator import context_requires
from action_machine.legacy.context_requires_intent import ContextRequiresIntent

__all__ = [
    "Context",
    "ContextRequiresIntent",
    "ContextView",
    "Ctx",
    "RequestInfo",
    "RuntimeInfo",
    "UserInfo",
    "context_requires",
]
