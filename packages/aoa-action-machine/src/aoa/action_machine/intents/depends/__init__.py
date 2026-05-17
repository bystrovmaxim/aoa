# packages/aoa-action-machine/src/aoa/action_machine/intents/depends/__init__.py
"""
Class-level ``@depends`` decorator for ``DependsIntent``.

═══════════════════════════════════════════════════════════════════════════════
``@depends`` and ``UseCase`` (UML-style action-to-action edges)
═══════════════════════════════════════════════════════════════════════════════

- **Targets:** ``BaseResource`` subclasses (service stubs, gateways) or concrete
  ``BaseAction`` subclasses. ``BaseAction`` itself is not a valid target.

- **``mode`` (action targets only):** use :data:`UseCase.include` when the host
  **always** runs the peer through the official execution path
  (``await box.run(Peer, …)`` / ``await machine.run(…, Peer, …)`` — i.e. entry
  into ``_run_internal`` for that type). After a **successful** root run, the
  production machine raises :exc:`~aoa.action_machine.exceptions.include_contract_violation_error.IncludeContractViolationError`
  if an ``include`` peer was never executed in that run. Use :data:`UseCase.extend`
  when the peer is optional or the host only resolves it via ``box.resolve`` until
  a later refactor adds an unconditional ``box.run``.

- **Resource targets:** ``mode`` must be omitted (``None``). ``UseCase`` applies
  only to action-to-action links.

- **Graph / interchange:** ``mode`` is stored on ``DependsGraphEdge`` and in wire
  JSON (see ``graph_json_schema``). The Maxitor DuckDB ``depends_edges`` table in
  the default v1 path does **not** add a separate ``mode`` column; consumers that
  need ``mode`` should read it from the full graph JSON (see project plan PR-0 /
  PR-3 branch 1).

Public exports: :func:`depends`, :class:`DependsIntent`, :class:`DependsEligible`,
:class:`UseCase`, :data:`VALID_USE_CASE_MODES`.
"""

from aoa.action_machine.intents.depends.depends_decorator import depends
from aoa.action_machine.intents.depends.depends_eligible import DependsEligible
from aoa.action_machine.intents.depends.depends_intent import DependsIntent
from aoa.action_machine.intents.depends.use_case import VALID_USE_CASE_MODES, UseCase

__all__ = [
    "VALID_USE_CASE_MODES",
    "DependsEligible",
    "DependsIntent",
    "UseCase",
    "depends",
]
