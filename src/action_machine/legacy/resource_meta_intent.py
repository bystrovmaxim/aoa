# src/action_machine/legacy/resource_meta_intent.py
"""``ResourceMetaIntent`` — marker mixin for the ``@meta`` decorator on resource managers."""

from __future__ import annotations

from typing import Any, ClassVar


class ResourceMetaIntent:
    """
AI-CORE-BEGIN
    ROLE: Marker contract for resource managers requiring @meta.
    CONTRACT: Resource manager hierarchy must provide _meta_info via decorator.
    INVARIANTS: Mixin is logic-free and used only by validators/inspectors.
    AI-CORE-END
"""

    _meta_info: ClassVar[dict[str, Any]]
