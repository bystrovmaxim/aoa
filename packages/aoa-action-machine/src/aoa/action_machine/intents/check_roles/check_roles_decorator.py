# packages/aoa-action-machine/src/aoa/action_machine/intents/check_roles/check_roles_decorator.py
"""
Decorator ``@check_roles`` — declare role requirements for action execution.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Declare which **role types** are required to execute an action. The decorator
writes a normalized specification to ``cls._role_info["spec"]``, consumed by
``ActionProductMachine`` / :class:`~aoa.action_machine.runtime.role_checker.RoleChecker`. The
spec must be ``GuestRole``, ``AnyRole``, a ``BaseRole`` subclass, or a
non-empty list of ``BaseRole`` subclasses (OR semantics). ``Context.user.roles``
holds the same ``BaseRole`` subclasses assigned to the user.

Roles may also be passed as :func:`~aoa.action_machine.intents.check_roles.grant.grant`
instances — bare roles and ``grant(...)`` instances may be mixed freely as
separate positional arguments. Each grant may carry its own ``when=`` condition
(evaluated against the user only); ``guard=`` is one additional condition shared
by every grant (evaluated against user and params). Both are stored on
``cls._role_info["grants"]`` / ``cls._role_info["guard"]`` — read from there by
:class:`~aoa.action_machine.graph.edges.role_graph_edge.RoleGraphEdge` (one edge
per grant, ``when`` in ``edge.properties["when"]``) and
:class:`~aoa.action_machine.graph.nodes.action_graph_node.ActionGraphNode`
(``guard`` in ``node.properties["guard"]``) when the interchange graph is built,
same as every other ``@check_roles`` fact.
:class:`~aoa.action_machine.runtime.role_checker.RoleChecker` reads the wired
graph, not ``_role_info``, at runtime in a later step — this decorator only
declares and validates the surface. ``when=``/``guard=`` must be synchronous
callables: ``async def`` raises
:exc:`~aoa.action_machine.exceptions.AccessConditionAsyncError` here, at class
definition time.

Every ``when=``/``guard=`` that can reject also carries its own mandatory
``reason=`` — ``Grant.reason`` for a grant's ``when=``, the decorator's own
``reason=`` for its ``guard=``. Both travel the same path as the condition they
belong to: ``Grant.reason`` becomes ``RoleGraphEdge.properties["when_reason"]``,
the decorator's ``reason=`` becomes ``cls._role_info["guard_reason"]`` and then
``ActionGraphNode.properties["guard_reason"]``. ``RoleChecker`` reads both back
at denial time and puts the matching one on the ``AuthorizationError`` it raises.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

    @check_roles(AdminRole)
    @check_roles(grant(AdminRole), grant(ManagerRole, when=..., reason=...), guard=..., reason=...)
            |
            v
    normalize spec / grants to role-type contract
            |
            v
    cls._role_info = {"spec": ..., "grants": [...], "guard": ..., "guard_reason": ...}
            |
            +--> mode validation (UNUSED error, DEPRECATED warning)
            +--> when=/guard= sync validation (AccessConditionAsyncError)
            +--> when=/reason= and guard=/reason= pairing validation (ValueError)
            |
            v
    Interchange ``RoleGraphEdge`` (per grant, carries "when"/"when_reason") +
    ``ActionGraphNode.properties["guard"]``/``["guard_reason"]`` (from "grants"/"guard") +
    ``RoleChecker`` at runtime

═══════════════════════════════════════════════════════════════════════════════
COMPONENTS
═══════════════════════════════════════════════════════════════════════════════

- ``check_roles``: public class decorator for action role requirements.
- ``_normalize_check_roles_spec``: accepted-shape validator + canonicalizer for the
  plain bare-role / list / sentinel form — used when no grant needs its own
  ``when=`` (``grant(...)`` stays optional; a bare role is shorthand for
  ``grant(role)`` with no condition).
- ``_normalize_grants``: validator + canonicalizer for the ``grant(...)``/mixed form.
- ``_spec_from_grants`` / ``_grants_for_normalized_spec``: convert between the two
  internal shapes so both forms populate the same ``_role_info`` keys.
- ``_validate_required_role_modes``: compile-time mode checks for declared roles.
- ``_reject_async_condition``: rejects ``async def`` in ``when=``/``guard=``.
- Target invariants: ensure class target.

"""

from __future__ import annotations

import asyncio
import warnings
from collections.abc import Callable
from typing import Any

from aoa.action_machine.auth.any_role import AnyRole
from aoa.action_machine.auth.base_role import BaseRole
from aoa.action_machine.auth.guest_role import GuestRole
from aoa.action_machine.exceptions.access_condition_async_error import AccessConditionAsyncError
from aoa.action_machine.intents.check_roles.grant import Grant
from aoa.action_machine.intents.role_mode.role_mode_decorator import RoleMode


def _normalize_check_roles_spec(spec: Any) -> Any:
    if spec is GuestRole or spec is AnyRole:
        return spec

    if isinstance(spec, str):
        raise TypeError(
            "@check_roles does not accept role name strings; pass a BaseRole "
            f"subclass, not {spec!r}. Use GuestRole or AnyRole for sentinel modes."
        )

    if isinstance(spec, type):
        if not issubclass(spec, BaseRole):
            raise TypeError(f"@check_roles expected a BaseRole subclass, got {spec!r}.")
        return spec

    if isinstance(spec, list):
        if len(spec) == 0:
            raise ValueError(
                "@check_roles: an empty role list was provided. " "Specify at least one role or use GuestRole."
            )
        if any(isinstance(x, str) for x in spec):
            raise TypeError("@check_roles does not accept list[str]; use a list of BaseRole " "subclasses only.")
        if not all(isinstance(x, type) for x in spec):
            raise TypeError("@check_roles: role list must contain only BaseRole subclasses; " f"got {spec!r}.")
        bad = [x for x in spec if not issubclass(x, BaseRole)]
        if bad:
            raise TypeError(
                "@check_roles: every list element must be a BaseRole " f"subclass; offending values: {bad!r}."
            )
        return tuple(spec)

    raise TypeError(
        f"@check_roles expects GuestRole, AnyRole, a BaseRole type, or a non-empty "
        f"list of BaseRole types; got {type(spec).__name__}: {spec!r}."
    )


def _grants_for_normalized_spec(normalized_spec: Any) -> list[Grant]:
    """Convert a normalized single-spec shape into the uniform ``list[Grant]`` shape.

    ``GuestRole``/``AnyRole`` are ``BaseRole`` subclasses themselves (sealed sentinels) and
    flow through as an ordinary grant, same as any concrete role — ``RoleGraphEdge.get_role_edges``
    (and ``RoleChecker`` downstream) rely on exactly one edge being built for them, same as today."""
    roles = normalized_spec if isinstance(normalized_spec, tuple) else (normalized_spec,)
    return [Grant(role=r, when=None) for r in roles]


def _normalize_grants(specs: tuple[Any, ...]) -> list[Grant]:
    """Validate and canonicalize the ``grant(...)``/bare-role mixed positional form."""
    grants: list[Grant] = []
    for item in specs:
        if isinstance(item, Grant):
            grants.append(item)
        elif isinstance(item, type) and issubclass(item, BaseRole):
            grants.append(Grant(role=item, when=None))
        else:
            raise TypeError(f"@check_roles expected a BaseRole subclass or grant(...), got {item!r}.")
    return grants


def _spec_from_grants(grants: list[Grant]) -> Any:
    """Derive the ``_role_info["spec"]`` shape (single type or tuple) from grants."""
    roles = tuple(g.role for g in grants)
    return roles[0] if len(roles) == 1 else roles


def _reject_async_condition(condition_name: str, func: Callable[..., Any]) -> None:
    """Raise :exc:`AccessConditionAsyncError` if ``func`` is ``async def``."""
    if asyncio.iscoroutinefunction(func):
        raise AccessConditionAsyncError(condition_name, func)


def _validate_required_role_modes(normalized: Any) -> None:
    """Reject ``UNUSED``; warn on ``DEPRECATED`` (``RoleChecker`` enforces ``SILENCED``)."""
    if normalized in (GuestRole, AnyRole):
        return
    reqs: tuple[type[BaseRole], ...] = (normalized,) if isinstance(normalized, type) else normalized
    for r in reqs:
        mode = RoleMode.declared_for(r)
        if mode is RoleMode.UNUSED:
            raise ValueError(f"@check_roles cannot require role {r.__qualname__!r}: " f"it is marked RoleMode.UNUSED.")
        if mode is RoleMode.DEPRECATED:
            warnings.warn(
                f"@check_roles references deprecated role {r.__qualname__!r}.",
                DeprecationWarning,
                stacklevel=3,
            )


def _target_is_class_invariant(cls: Any) -> None:
    if not isinstance(cls, type):
        raise TypeError(
            f"@check_roles can only be applied to a class. " f"Got object of type {type(cls).__name__}: {cls!r}."
        )


def check_roles(*specs: Any, guard: Callable[..., bool] | None = None, reason: str | None = None) -> Any:
    """
    Class-level decorator that declares role requirements for an action.

    ``grant(...)`` and ``guard=`` are optional, not a legacy form to migrate away
    from: a bare role (or a list of roles, or ``GuestRole``/``AnyRole``) is plain
    shorthand for "this role, no extra condition" — reach for ``grant(role,
    when=...)`` only when a role actually needs one. Bare roles and ``grant(...)``
    instances may be mixed freely as separate positional arguments. ``guard=`` is
    one additional condition shared by every grant. See module docstring for
    details.

    ``guard=`` and ``reason=`` are given together or not at all — same rule as
    ``grant(when=..., reason=...)``: a condition that can reject the request must
    also say why. ``check_roles()`` only supports one ``guard=``/``reason=`` pair
    per action today (several denial reasons behind one shared guard is an open
    question, not solved here); several *role-level* reasons are already possible
    via several ``grant(role, when=..., reason=...)`` calls.

    Raises:
        TypeError: no role or grant(...) was given at all.
        ValueError: exactly one of ``guard``/``reason`` was given.
    """
    if len(specs) == 0:
        raise TypeError("@check_roles requires at least one role or grant(...).")
    if (guard is None) != (reason is None):
        raise ValueError(
            "@check_roles: guard= and reason= must be given together, or not at all — "
            f"got guard={guard!r}, reason={reason!r}."
        )

    if len(specs) == 1 and not isinstance(specs[0], Grant):
        normalized_spec = _normalize_check_roles_spec(specs[0])
        grants = _grants_for_normalized_spec(normalized_spec)
    else:
        grants = _normalize_grants(specs)
        normalized_spec = _spec_from_grants(grants)

    _validate_required_role_modes(normalized_spec)
    for g in grants:
        if g.when is not None:
            _reject_async_condition("when", g.when)
    if guard is not None:
        _reject_async_condition("guard", guard)

    def decorator(cls: Any) -> Any:
        _target_is_class_invariant(cls)

        cls._role_info = {"spec": normalized_spec, "grants": grants, "guard": guard, "guard_reason": reason}
        return cls

    return decorator
