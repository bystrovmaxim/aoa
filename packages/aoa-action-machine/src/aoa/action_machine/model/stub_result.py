# packages/aoa-action-machine/src/aoa/action_machine/model/stub_result.py
"""
``StubResult`` — minimal ``BaseResult`` subclass for tests and tooling.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Real actions must bind concrete result schemas (subclasses of ``BaseResult``).
Graph inspectors skip the abstract root ``BaseResult`` axis node, so
``BaseAction[..., BaseResult]`` yields dangling result edges. Use ``StubResult`` when an
empty output contract is enough. Pair with
:class:`~aoa.action_machine.model.stub_params.StubParams` for ``P`` when only the params axis
needs a stub.

═══════════════════════════════════════════════════════════════════════════════
ARCHITECTURE / DATA FLOW
═══════════════════════════════════════════════════════════════════════════════

::

    BaseResult -> StubResult -> empty action output contract

"""

from __future__ import annotations

from aoa.action_machine.model.base_result import BaseResult


class StubResult(BaseResult):
    """
    AI-CORE-BEGIN
    ROLE: Canonical minimal result type for non-production ``BaseAction`` bindings.
    CONTRACT: Strict subclass of ``BaseResult`` so result-axis graph nodes materialize.
    INVARIANTS: No fields; frozen/forbid inherited from ``BaseResult``.
    AI-CORE-END
    """

    pass
