# packages/aoa-action-machine/src/aoa/action_machine/auth/permission_namespace.py
"""
``compute_cache_partition`` — the opaque per-identity label behind ``PermissionNamespace``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A client that caches resolver answers needs to tag each cached entry with "whose
answer is this" — otherwise a cache mistakenly shared across two identities is a
privilege leak, not just a stale answer. That tag must not be something the
client assembles itself from values it holds (a stale variable, a key built
before an account switch actually applied) — it has to come from the server,
which is the only party that reliably knows who is asking right now.

``compute_cache_partition(context)`` is that tag: a deterministic, opaque string
derived from the authenticated ``Context``. Opaque means the client never parses
or reconstructs it — it just carries the string it was given and attaches it to
its cache key. Deterministic means the *same* identity, right now, always maps
to the *same* label; a *different* identity — a different ``user_id``, or the
same user with a different ``roles`` set — always maps to a *different* one.

═══════════════════════════════════════════════════════════════════════════════
WHY THIS DOUBLES AS "GENERATION" WITHOUT A STORED COUNTER
═══════════════════════════════════════════════════════════════════════════════

The design this module is part of (``PermissionNamespace``) calls for the label
to change whenever the caller's identity meaningfully changes — logging in as a
different user, or a role being granted/revoked. Rather than track that with a
separate, server-stored "generation" counter (which would need session storage
this stateless, per-request-JWT-verification framework does not have), the label
is simply *recomputed from the current identity on every call*: a different
``user_id`` or a different ``roles`` tuple hashes to a different string, for
free, with no state to keep in sync. Logging out has no partition to serve at
all — there is no authenticated ``Context`` to compute one from.

The one case this formula does **not** cover on its own is revoking a still
technically-valid credential (e.g. a JWT that has not yet expired) — that is a
property of whatever the ``AuthCoordinator``/``Authenticator`` in front of this
function does (a revocation check that makes ``process()`` return ``None`` for
a revoked token), not something ``compute_cache_partition`` can detect from the
``Context`` alone. Once a coordinator rejects a revoked identity, no ``Context``
is ever constructed for it and no partition is ever issued going forward.

``Context.user`` carries no ``tenant_id`` today — if a future ``Context`` gains
one, it belongs in the hashed identity below, the same way ``roles`` already is.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aoa.action_machine.context.context import Context


def compute_cache_partition(context: Context) -> str:
    """
    Derive the opaque ``cache_partition`` label for one authenticated identity.

    Hashes ``user_id`` together with the sorted set of role *names* (``BaseRole.name``
    — the same stable, wire-safe strings ``UserInfo`` already serializes roles as,
    not the Python class objects themselves). Sorting makes the input
    order-independent: ``roles=(A, B)`` and ``roles=(B, A)`` are the same identity
    and must produce the same label. An anonymous ``Context`` (``user_id=None``,
    no roles) still hashes to a stable, well-defined string — nothing here is
    optional or ``None``.

    ``user_id is not None`` is hashed in explicitly, ahead of ``user_id`` itself:
    nothing on ``UserInfo`` forbids ``user_id=""`` (it is a plain, generic schema
    field, not exclusively a real-identity contract), and an ``f"{user_id or ''}"``
    default would hash an authenticated caller with an empty ``user_id`` to the
    *same* string as a genuinely anonymous one with the same roles — a privilege
    leak waiting on whatever ``AuthCoordinator`` happens to be in front of this
    function. The explicit flag keeps the two states apart regardless of what
    ``user_id`` actually contains.
    """
    user_id = context.user.user_id
    roles = ",".join(sorted(role.name for role in context.user.roles))
    identity = f"{user_id is not None}:{user_id or ''}|{roles}"
    return hashlib.sha256(identity.encode()).hexdigest()
