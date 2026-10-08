# packages/aoa-action-machine/src/aoa/action_machine/exceptions/intent_resolution_error.py
"""``IntentResolutionError`` — the resolver was handed something it cannot read as a declaration."""

from __future__ import annotations


class IntentResolutionError(ValueError):
    """
    An intent resolver was handed something that is not the callable or property exposing the
    declaration it resolves.
    """

    pass
