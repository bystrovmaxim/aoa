# src/action_machine/intents/meta/action_meta_intent.py
"""``ActionMetaIntent`` — marker mixin for the ``@meta`` decorator on actions."""

from __future__ import annotations

from typing import Any, ClassVar


class ActionMetaIntent:
    """
    Intent marker: action types participate in the ``@meta`` grammar.

    ``BaseAction`` includes this mixin. Subclasses must follow ``@meta`` rules
    enforced by the decorator. ``@meta`` sets
    ``_meta_info`` with ``description`` and ``domain``.

    AI-CORE-BEGIN
    ROLE: Marker contract for action classes requiring meta declarations.
    CONTRACT: Action hierarchy carries this marker for @meta enforcement.
    INVARIANTS: Mixin is logic-free and stores no runtime behavior.
    AI-CORE-END
    """

    _meta_info: ClassVar[dict[str, Any]]
