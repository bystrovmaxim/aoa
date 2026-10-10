# packages/aoa-demo/src/aoa/demo/model/generalization_shapes/generalization_shapes_domain.py
"""
GeneralizationShapesDomain — the bounded context whose fixtures draw inheritance edges.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

``GeneralizationShapesDomain`` is the bounded context of the generalization
demonstrator. It carries no business meaning: every action and entity in this
domain exists to produce one generalization shape Maxitor can draw — a
``parent_action`` inheritance edge on the use-case diagram or a
``parent_entity`` inheritance edge on the ERD.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    GeneralizationShapesDomain (marker)
        ├── actions/   — parent action with two children (parent_action edges)
        └── entities/  — parent entity with one child (parent_entity edge)

The domain is registered in ``aoa.demo.model.build._MODULES`` alongside the
other demo domains.
"""

from __future__ import annotations

from aoa.action_machine.domain import BaseDomain


class GeneralizationShapesDomain(BaseDomain):
    """
    AI-CORE-BEGIN
    ROLE: Bounded-context marker for the generalization drawing fixtures.
    CONTRACT: ``name`` and ``description`` are non-empty class attributes; no
        member of this domain implies a business meaning.
    INVARIANTS: The domain exists for the diagram, not for a product.
    AI-CORE-END
    """

    name = "generalization_shapes"
    description = "Drawing fixtures for generalization shapes: parent_action and parent_entity inheritance edges"
