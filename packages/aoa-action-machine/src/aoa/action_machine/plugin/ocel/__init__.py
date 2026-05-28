# packages/aoa-action-machine/src/aoa/action_machine/plugin/ocel/__init__.py
"""
OCEL 2.0 export for ActionMachine — optional extra ``aoa-action-machine[ocel]``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Aspects return ``list[OcelFrame]``; ``OcelPlugin`` builds ``OcelEvent`` on
``GlobalFinishEvent``. Export policy (loaded FK → E2O, one hop, no O2O v1):
``packages/aoa-action-machine/src/aoa/action_machine/plugin/ocel/README.md``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    aspect → list[OcelFrame] (partial entity controls loaded relations)
              │
              ▼
    OcelPlugin → OcelEvent (E2O + OcelObject attributes) → OcelStoreResource
"""

from __future__ import annotations

from aoa.action_machine.plugin.ocel.contracts import OcelFrame
from aoa.action_machine.plugin.ocel.plugin import OCEL_FRAMES_KEY, OcelPlugin
from aoa.action_machine.plugin.ocel.resource import InMemoryOcelStoreResource, OcelStoreResource
from aoa.action_machine.plugin.ocel.type_id import make_oid

__all__ = [
    "OCEL_FRAMES_KEY",
    "InMemoryOcelStoreResource",
    "OcelFrame",
    "OcelPlugin",
    "OcelStoreResource",
    "make_oid",
]
