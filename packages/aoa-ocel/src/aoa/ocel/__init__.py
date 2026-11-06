# packages/aoa-ocel/src/aoa/ocel/__init__.py
"""
OCEL 2.0 export plugin for AOA — install with ``pip install aoa-ocel``.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Aspects return ``list[OcelFrame]``; ``OcelPlugin`` builds ``OcelEvent`` on
``GlobalFinishEvent``. Export policy (loaded FK → E2O, one hop, no O2O v1):
``packages/aoa-ocel/src/aoa/ocel/README.md``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    aspect → list[OcelFrame] (partial entity controls loaded relations)
              │
              ▼
    OcelPlugin → OcelEvent (E2O + OcelObject attributes) → OcelStorage
"""

from __future__ import annotations

from aoa.ocel.contracts import OcelFrame
from aoa.ocel.plugin import OCEL_FRAMES_KEY, OcelPlugin
from aoa.ocel.resource import InMemoryOcelStorage, OcelStorage
from aoa.ocel.type_id import make_oid

__all__ = [
    "OCEL_FRAMES_KEY",
    "InMemoryOcelStorage",
    "OcelFrame",
    "OcelPlugin",
    "OcelStorage",
    "make_oid",
]
