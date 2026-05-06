# src/action_machine/model/result_stub.py
"""
``ResultStub`` — minimal ``BaseResult`` subclass for tests and tooling.

═══════════════════════════════════════════════════════════════════════════════
PURPOSE
═══════════════════════════════════════════════════════════════════════════════

Real actions must bind concrete result schemas (subclasses of ``BaseResult``).
Graph inspectors skip the abstract root ``BaseResult`` axis node, so
``BaseAction[..., BaseResult]`` yields dangling result edges. Use ``ResultStub`` when an
empty output contract is enough. Pair with
:class:`~action_machine.model.params_stub.ParamsStub` for ``P`` when only the params axis
needs a stub.
"""

from __future__ import annotations

from action_machine.model.base_result import BaseResult


class ResultStub(BaseResult):
    """
    AI-CORE-BEGIN
    ROLE: Canonical minimal result type for non-production ``BaseAction`` bindings.
    CONTRACT: Strict subclass of ``BaseResult`` so result-axis graph nodes materialize.
    INVARIANTS: No fields; frozen/forbid inherited from ``BaseResult``.
    AI-CORE-END
    """

    pass
