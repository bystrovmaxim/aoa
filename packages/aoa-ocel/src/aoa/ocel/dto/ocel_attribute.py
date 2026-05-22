# packages/aoa-ocel/src/aoa/ocel/dto/ocel_attribute.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class OcelAttribute:
    """Named attribute of an event or object (no ``time`` field = static)."""

    name: str
    value: Any
