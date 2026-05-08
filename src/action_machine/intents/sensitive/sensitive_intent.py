# src/action_machine/intents/sensitive/sensitive_intent.py
"""``SensitiveIntent`` — marker mixin for ``@sensitive`` property declarations."""

from __future__ import annotations


class SensitiveIntent:
    """
    AI-CORE-BEGIN
    ROLE: Marker contract for classes whose members use ``@sensitive`` masking config.
    CONTRACT: Action and schema hierarchies inherit this marker; graph builders read
        ``fget._sensitive_config`` via :class:`~action_machine.intents.sensitive.sensitive_intent_resolver.SensitiveIntentResolver`.
    INVARIANTS: Mixin is logic-free.
    AI-CORE-END
    """

    pass
