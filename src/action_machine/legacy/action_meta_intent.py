# src/action_machine/legacy/action_meta_intent.py
"""``ActionMetaIntent`` — marker mixin for the ``@meta`` decorator on actions."""

from __future__ import annotations

from typing import Any, ClassVar


class ActionMetaIntent:
    """
AI-CORE-BEGIN
    ROLE: Marker contract for action classes requiring meta declarations.
    CONTRACT: Action hierarchy carries this marker for @meta enforcement.
    INVARIANTS: Mixin is logic-free and stores no runtime behavior.
    AI-CORE-END
"""

    _meta_info: ClassVar[dict[str, Any]]
