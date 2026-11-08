# packages/aoa-action-machine/src/aoa/action_machine/resources/entities/__init__.py
"""
The return check of a resource — the plan of its entities and the walk of an answer.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A resource **is** a database: its ``@entities`` declaration lists the classes it may
return, and every public method's answer is walked against that list. This package
holds the two halves of that check:

- :mod:`~aoa.action_machine.resources.entities.plan` — a frozen plan per concrete
  resource class: the listed classes and, for each, whether a relation reachable
  from it leads outside the list. ``NodeGraphCoordinator.build`` attaches it to
  every resource node; the first public call computes it lazily when a resource is
  used without a machine.
- :mod:`~aoa.action_machine.resources.entities.walk` — ``walk_answer``, which walks
  an answer by that plan and raises ``ResourceEntitiesError`` for an entity the
  resource does not list.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    @entities(OrderCoreEntity, ...)             entity relation metadata
              │                                            │
              └───────────────┬────────────────────────────┘
                              ▼
                    EntitiesPlan (frozen data)
                              │  stored in cls.__dict__['_entities_plan']
                              ▼
    public method wrapper → walk_answer(answer, plan, resource, entry_point, path)
                              │
                              ├─ listed entity          → passes
                              ├─ dictionary/state       → passes
                              └─ unlisted entity        → ResourceEntitiesError
"""

from __future__ import annotations

__all__: list[str] = []
