# packages/aoa-action-machine/src/aoa/action_machine/domain/state_spec.py
"""
StateSpec — the status declaration placeholder used inside a state type body.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

A state type declares its statuses in its own class body::

    class OrderStateEntity(BaseStateEntity):
        DRAFT = OrderStateEntity(code="draft", display_name="Draft")

The class does not exist while its body runs, so the name resolves to the
internal factory in this module instead. The factory returns a ``StateSpec``
that holds the arguments; the Pydantic hook on ``BaseStateEntity`` turns every
placeholder into a real instance after the model is built.

═══════════════════════════════════════════════════════════════════════════════
SCOPE (IN / OUT)
═══════════════════════════════════════════════════════════════════════════════

**In scope**
    Holding the raw keyword arguments of one declaration and nothing else.

**Out of scope**
    Validation — the real class validates its own fields when the hook builds
    the instance. The catalogue and the refusals — ``BaseStateEntity`` and
    ``Lifecycle``.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    class body: DRAFT = OrderStateEntity(...)   ──►  StateSpec(kwargs)
    class creation: __pydantic_init_subclass__  ──►  OrderStateEntity(**kwargs)

The placeholder is listed in ``BaseStateEntity.model_config['ignored_types']``,
so Pydantic does not treat it as a model field.
"""

from __future__ import annotations

from typing import Any


class StateSpec:
    """Hold the keyword arguments of one status declaration until the class exists."""

    def __init__(self, kwargs: dict[str, Any]) -> None:
        """Store the declaration's arguments verbatim."""
        self.kwargs = kwargs


def state(**kwargs: Any) -> StateSpec:
    """Declare a status inside a state type body; the class turns it into an instance."""
    return StateSpec(kwargs)
