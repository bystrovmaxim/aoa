# src/action_machine/intents/meta/meta_intent.py
"""``MetaIntent`` — marker mixin for the ``@meta`` decorator on actions and resource managers."""

from __future__ import annotations

from typing import Any, ClassVar


class MetaIntent:
    """
    AI-CORE-BEGIN
    ROLE: Marker contract for classes that carry ``@meta`` declarations.
    CONTRACT: Action and resource hierarchies inherit this marker for @meta enforcement.
    INVARIANTS: Mixin is logic-free and stores no runtime behavior.
    AI-CORE-END
    """

    _meta_info: ClassVar[dict[str, Any]]
